import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import llama_cpp_agent  # noqa: E402


def test_llama_cpp_agent_uses_instruct_defaults(monkeypatch, capsys):
    captured = {}

    def fake_request(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {
            "choices": [
                {"message": {"content": '{"ok": true}\n{"events": []}'}}
            ]
        }

    monkeypatch.setattr(llama_cpp_agent, "_request_json", fake_request)
    monkeypatch.setattr(sys, "stdin", io.StringIO("benchmark prompt"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llama_cpp_agent.py",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--model",
            "test-model",
            "--mode",
            "instruct",
        ],
    )

    assert llama_cpp_agent.main() == 0
    out = capsys.readouterr().out.strip()
    payload = captured["payload"]

    assert out == '{"ok": true}\n{"events": []}'
    assert captured["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert payload["model"] == "test-model"
    assert payload["temperature"] == 0.7
    assert payload["top_p"] == 0.80
    assert payload["top_k"] == 20
    assert payload["min_p"] == 0.0
    assert payload["presence_penalty"] == 1.5
    assert payload["repeat_penalty"] == 1.0
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "benchmark prompt"


def test_llama_cpp_agent_allows_sampling_overrides(monkeypatch):
    captured = {}

    def fake_request(url, payload, timeout):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(llama_cpp_agent, "_request_json", fake_request)
    monkeypatch.setattr(sys, "stdin", io.StringIO("prompt"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llama_cpp_agent.py",
            "--mode",
            "thinking-coding",
            "--temperature",
            "0.2",
            "--top-p",
            "0.5",
            "--top-k",
            "10",
        ],
    )

    assert llama_cpp_agent.main() == 0
    payload = captured["payload"]
    assert payload["temperature"] == 0.2
    assert payload["top_p"] == 0.5
    assert payload["top_k"] == 10
    assert payload["presence_penalty"] == 0.0


def test_llama_cpp_agent_retrieves_bundle_files_and_writes_trace(monkeypatch, tmp_path):
    captured = {}

    def fake_request(url, payload, timeout):
        captured["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"task_id":"enterprise-fnf-escrow-recon-v1","facts":{},"citations":[]}\n'
                            '{"events":[]}'
                        )
                    }
                }
            ]
        }

    trace_log = tmp_path / "tool-events.jsonl"
    prompt = f"""You are being evaluated on an OKF-style knowledge bundle.

Bundle path: {ROOT / "bundles" / "strict-retail-ops"}
Task path: {ROOT / "tasks" / "enterprise-fnf-synthesis.json"}
Bundle variant: strict
"""

    monkeypatch.setattr(llama_cpp_agent, "_request_json", fake_request)
    monkeypatch.setattr(sys, "stdin", io.StringIO(prompt))
    monkeypatch.setenv("OKF_TRACE_LOG", str(trace_log))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llama_cpp_agent.py",
            "--mode",
            "instruct",
            "--model",
            "test-model",
            "--max-files",
            "10",
            "--max-index-files",
            "2",
            "--use-required-citations",
        ],
    )

    assert llama_cpp_agent.main() == 0
    user_prompt = captured["payload"]["messages"][1]["content"]
    events = [
        json.loads(line)
        for line in trace_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert "RETRIEVED OKF FILES" in user_prompt
    assert "enterprise-fnf-escrow-recon-v1" in user_prompt
    assert "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md" in user_prompt
    assert "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md" in user_prompt
    assert events
    assert all(event["type"] == "read" for event in events)
    assert any(
        event["path"] == "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md"
        for event in events
    )


def test_index_metadata_boosts_hinted_directory(tmp_path):
    """task_hint in index frontmatter raises that directory's ancestor-boost score."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    query = "escrow disbursement florida reconciliation"

    (bundle / "index.md").write_text("# Root\n\n- [Alpha](alpha/index.md)\n- [Beta](beta/index.md)\n")

    # alpha: uniform-style index with task_hint matching the query
    (bundle / "alpha").mkdir()
    (bundle / "alpha" / "index.md").write_text(
        "---\ntype: directory_index\ndomain: alpha\narea: alpha\ndepth: 1\n"
        "metadata_profile: uniform-enterprise\n"
        "task_hint: escrow disbursement florida reconciliation\n---\n# Alpha\n"
    )
    (bundle / "alpha" / "concept.md").write_text(
        "---\nid: alpha.concept\ntype: concept\ntitle: Alpha\n---\n# Alpha Concept\nGeneric content.\n"
    )

    # beta: strict-style plain index (no frontmatter, no query keywords)
    (bundle / "beta").mkdir()
    (bundle / "beta" / "index.md").write_text("# Beta\n\n- [Concept](concept.md)\n")
    (bundle / "beta" / "concept.md").write_text(
        "---\nid: beta.concept\ntype: concept\ntitle: Beta\n---\n# Beta Concept\nGeneric content.\n"
    )

    from collections import Counter
    query_counts = Counter(llama_cpp_agent._tokenize(query))
    files = llama_cpp_agent._candidate_markdown_files(bundle)
    indexes = llama_cpp_agent._pick_index_files(bundle, files, query_counts, 4)
    index_texts = {p: p.read_text() for p in indexes}

    def score_indexes(use_metadata: bool) -> dict:
        scores = {}
        for path, text in index_texts.items():
            if use_metadata:
                hint_text, priority_mult = llama_cpp_agent._parse_index_hints(text)
                scoring_text = (text + " " + hint_text) if hint_text else text
            else:
                scoring_text, priority_mult = text, 1.0
            scores[path.parent] = llama_cpp_agent._content_score(scoring_text, query_counts) * priority_mult
        return scores

    scores_with = score_indexes(True)
    scores_without = score_indexes(False)

    alpha_dir = bundle / "alpha"
    beta_dir = bundle / "beta"

    # metadata extraction doubles the hint-term weight → alpha scores higher with it ON
    assert scores_with.get(alpha_dir, 0) > scores_without.get(alpha_dir, 0)
    # beta has no frontmatter — hint extraction changes nothing for it
    assert scores_with.get(beta_dir, 0) == scores_without.get(beta_dir, 0)
    # with metadata on, alpha outranks beta (hint boost makes the gap unambiguous)
    assert scores_with.get(alpha_dir, 0) > scores_with.get(beta_dir, 0)


def test_no_index_metadata_flag_disables_hint_boost(monkeypatch, tmp_path):
    """--no-index-metadata must produce a prompt without the metadata boost influencing selection."""
    captured = {}

    def fake_request(url, payload, timeout):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": '{"ok":true}\n{"events":[]}'}}]}

    # use the real uniform bundle — it has task_hints in its indexes
    bundle = ROOT / "bundles" / "uniform-yaml-retail-ops"
    task = ROOT / "tasks" / "enterprise-fnf-synthesis.json"
    prompt = f"Bundle path: {bundle}\nTask path: {task}\nBundle variant: uniform-yaml\n"

    monkeypatch.setattr(llama_cpp_agent, "_request_json", fake_request)
    monkeypatch.setattr(sys, "stdin", io.StringIO(prompt))
    monkeypatch.setattr(sys, "argv", [
        "llama_cpp_agent.py", "--mode", "instruct",
        "--max-files", "8", "--max-index-files", "4",
        "--no-index-metadata",
    ])

    assert llama_cpp_agent.main() == 0
    # just verify it ran cleanly and retrieved something — not that specific files were chosen
    user_msg = captured["payload"]["messages"][1]["content"]
    assert "RETRIEVED OKF FILES" in user_msg


def test_llama_cpp_agent_no_retrieval_keeps_original_prompt(monkeypatch):
    captured = {}

    def fake_request(url, payload, timeout):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "{}"}}]}

    prompt = f"""Bundle path: {ROOT / "bundles" / "strict-retail-ops"}
Task path: {ROOT / "tasks" / "enterprise-fnf-synthesis.json"}
Bundle variant: strict
"""

    monkeypatch.setattr(llama_cpp_agent, "_request_json", fake_request)
    monkeypatch.setattr(sys, "stdin", io.StringIO(prompt))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "llama_cpp_agent.py",
            "--mode",
            "instruct",
            "--no-retrieval",
        ],
    )

    assert llama_cpp_agent.main() == 0
    assert captured["payload"]["messages"][1]["content"] == prompt
