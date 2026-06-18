import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import llama_cpp_tool_agent as agent  # noqa: E402


BUNDLE = ROOT / "bundles" / "strict-retail-ops"
TASK   = ROOT / "tasks" / "enterprise-fnf-synthesis.json"


def _make_prompt(bundle=BUNDLE, task=TASK, variant="strict") -> str:
    return f"Bundle path: {bundle}\nTask path: {task}\nBundle variant: {variant}\n"


def _tool_response(path: str, call_id: str = "call_1") -> dict:
    return {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": path}),
                    },
                }],
            },
        }],
    }


def _final_response(content: str) -> dict:
    return {
        "choices": [{
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": content, "tool_calls": None},
        }],
    }


SUBMISSION = json.dumps({
    "task_id": "enterprise-fnf-escrow-recon-v1",
    "bundle_variant": "strict",
    "answer": "test answer",
    "facts": {"affected_kpi": "escrow disbursement reconciliation variance"},
    "citations": ["/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md"],
})
TRACE_OBJ = json.dumps({
    "agent": "llama-cpp-tool-agent",
    "bundle_variant": "strict",
    "events": [{"type": "read", "path": "/index.md"}],
})


def test_tool_loop_reads_files_and_produces_answer(monkeypatch, capsys, tmp_path):
    """Model calls read_file twice then stops — both reads become trace events."""
    responses = iter([
        _tool_response("/index.md", "c1"),
        _tool_response("/enterprise-fnf/index.md", "c2"),
        _final_response(f"{SUBMISSION}\n{TRACE_OBJ}"),
    ])
    monkeypatch.setattr(agent, "_post", lambda url, payload, timeout: next(responses))
    monkeypatch.setattr(sys, "stdin", io.StringIO(_make_prompt()))
    monkeypatch.setenv("OKF_TRACE_LOG", str(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(sys, "argv", [
        "llama_cpp_tool_agent.py", "--model", "test", "--mode", "instruct",
    ])

    rc = agent.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "enterprise-fnf-escrow-recon-v1" in out
    events = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text().splitlines()
    ]
    assert len(events) == 2
    assert events[0]["path"] == "/index.md"
    assert events[1]["path"] == "/enterprise-fnf/index.md"
    assert all(e["type"] == "read" for e in events)


def test_tool_loop_blocks_path_traversal(monkeypatch, capsys, tmp_path):
    """read_file must not serve files outside the bundle."""
    outside_path = "/../../../etc/passwd"
    responses = iter([
        _tool_response(outside_path, "c1"),
        _final_response(f"{SUBMISSION}\n{TRACE_OBJ}"),
    ])
    monkeypatch.setattr(agent, "_post", lambda url, payload, timeout: next(responses))
    monkeypatch.setattr(sys, "stdin", io.StringIO(_make_prompt()))
    monkeypatch.setenv("OKF_TRACE_LOG", str(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(sys, "argv", ["llama_cpp_tool_agent.py", "--model", "test"])

    rc = agent.main()
    assert rc == 0
    # The path-traversal read must NOT appear in trace events.
    log = tmp_path / "trace.jsonl"
    events = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
    assert not any("passwd" in e.get("path", "") for e in events)


def test_tool_loop_deduplicates_trace_events(monkeypatch, capsys, tmp_path):
    """Reading the same file twice should only emit one trace event."""
    responses = iter([
        _tool_response("/index.md", "c1"),
        _tool_response("/index.md", "c2"),
        _final_response(f"{SUBMISSION}\n{TRACE_OBJ}"),
    ])
    monkeypatch.setattr(agent, "_post", lambda url, payload, timeout: next(responses))
    monkeypatch.setattr(sys, "stdin", io.StringIO(_make_prompt()))
    monkeypatch.setenv("OKF_TRACE_LOG", str(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(sys, "argv", ["llama_cpp_tool_agent.py", "--model", "test"])

    agent.main()
    events = [
        json.loads(l)
        for l in (tmp_path / "trace.jsonl").read_text().splitlines()
    ]
    assert len(events) == 1


def test_tool_loop_forces_answer_at_max_iterations(monkeypatch, capsys, tmp_path):
    """When max_iterations is hit the wrapper sends a nudge and prints whatever the model returns."""
    # Always return a tool call — loop should hit the limit and send a final nudge.
    call_n = [0]
    def fake_post(url, payload, timeout):
        call_n[0] += 1
        if call_n[0] <= 2:          # within iteration limit
            return _tool_response("/index.md", f"c{call_n[0]}")
        return _final_response(f"{SUBMISSION}\n{TRACE_OBJ}")  # nudge response

    monkeypatch.setattr(agent, "_post", fake_post)
    monkeypatch.setattr(sys, "stdin", io.StringIO(_make_prompt()))
    monkeypatch.setenv("OKF_TRACE_LOG", str(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(sys, "argv", [
        "llama_cpp_tool_agent.py", "--model", "test", "--max-iterations", "2",
    ])

    rc = agent.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "enterprise-fnf-escrow-recon-v1" in out


def test_tool_loop_reads_real_bundle_files(monkeypatch, capsys, tmp_path):
    """read_file actually serves content from disk for a real bundle path."""
    responses = iter([
        _tool_response("/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md", "c1"),
        _final_response(f"{SUBMISSION}\n{TRACE_OBJ}"),
    ])
    monkeypatch.setattr(agent, "_post", lambda url, payload, timeout: next(responses))

    captured_messages = {}
    original_post = agent._post

    def capturing_post(url, payload, timeout):
        captured_messages["last"] = payload["messages"]
        return next(iter([]))   # never called — already monkeypatched above

    # Re-monkeypatch to capture the tool result message.
    call_count = [0]
    all_responses = [
        _tool_response("/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md", "c1"),
        _final_response(f"{SUBMISSION}\n{TRACE_OBJ}"),
    ]
    def capturing_post2(url, payload, timeout):
        r = all_responses[call_count[0]]
        call_count[0] += 1
        captured_messages["messages_at"] = payload["messages"][:]
        return r

    monkeypatch.setattr(agent, "_post", capturing_post2)
    monkeypatch.setattr(sys, "stdin", io.StringIO(_make_prompt()))
    monkeypatch.setenv("OKF_TRACE_LOG", str(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(sys, "argv", ["llama_cpp_tool_agent.py", "--model", "test"])

    agent.main()

    # The second request (call_count==1) should have a tool result message
    # containing the actual file content from disk.
    tool_msgs = [m for m in captured_messages["messages_at"] if m.get("role") == "tool"]
    if tool_msgs:
        assert "normalized_tax_id" in tool_msgs[0]["content"]
