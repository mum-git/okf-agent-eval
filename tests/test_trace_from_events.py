"""Tests for scripts/trace_from_events.py — the native-event trace adapter.

Sample event shapes are taken verbatim from the installed CLIs:
  codex     `codex exec --json`
  opencode  `opencode run --format json`
  claude    `claude --output-format stream-json --verbose`
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "trace_from_events", ROOT / "scripts" / "trace_from_events.py"
)
tfe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tfe)


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    """A bundle root with a couple of files, exported via OKF_BUNDLE_PATH."""
    (tmp_path / "incidents").mkdir()
    (tmp_path / "incidents" / "root-cause.md").write_text("rc", encoding="utf-8")
    (tmp_path / "incidents" / "remediation.md").write_text("rm", encoding="utf-8")
    (tmp_path / "metrics").mkdir()
    (tmp_path / "metrics" / "net-margin.md").write_text("nm", encoding="utf-8")
    monkeypatch.setenv("OKF_BUNDLE_PATH", str(tmp_path))
    return tmp_path


def _emit(fmt, text, bundle):
    emitter = tfe.TraceEmitter(fmt, tfe._bundle_root())
    answer, tokens = tfe.PARSERS[fmt](text, emitter)
    return answer, tokens, sorted(emitter._seen)


def test_codex_extracts_shell_cat_reads(bundle):
    """codex reads files via shell cat/sed — the path lives in `command`."""
    rc = bundle / "incidents" / "root-cause.md"
    nm = bundle / "metrics" / "net-margin.md"
    text = "\n".join(json.dumps(e) for e in [
        {"type": "thread.started"},
        {"type": "item.completed", "item": {
            "type": "command_execution",
            "command": f"/bin/bash -lc 'cat {rc}'", "exit_code": 0}},
        {"type": "item.completed", "item": {
            "type": "command_execution",
            "command": f"/bin/bash -lc \"sed -n '1,40p' {nm}\"", "exit_code": 0}},
        {"type": "item.completed", "item": {
            "type": "agent_message", "text": '{"task_id":"x"}'}},
        {"type": "turn.completed", "usage": {
            "input_tokens": 16965, "output_tokens": 80}},
    ])
    answer, tokens, seen = _emit("codex", text, bundle)
    assert seen == ["/incidents/root-cause.md", "/metrics/net-margin.md"]
    assert answer == '{"task_id":"x"}'
    assert tokens == 16965 + 80


def test_opencode_read_tool_and_bash(bundle):
    rc = bundle / "incidents" / "root-cause.md"
    rm = bundle / "incidents" / "remediation.md"
    text = "\n".join(json.dumps(e) for e in [
        {"type": "tool_use", "part": {"tool": "read", "state": {
            "status": "completed", "input": {"filePath": str(rc)}}}},
        {"type": "tool_use", "part": {"tool": "bash", "state": {
            "status": "completed", "input": {"command": f"cat {rm}"}}}},
        {"type": "tool_use", "part": {"tool": "grep", "state": {
            "status": "completed", "input": {"pattern": "margin", "path": str(bundle)}}}},
        {"type": "text", "part": {"text": '{"task_id":"x"}'}},
        {"type": "step_finish", "part": {"tokens": {"total": 9889}}},
        {"type": "step_finish", "part": {"tokens": {"total": 1200}}},
    ])
    answer, tokens, seen = _emit("opencode", text, bundle)
    # read tool + bash cat are reads; grep is not a file read.
    assert seen == ["/incidents/remediation.md", "/incidents/root-cause.md"]
    assert answer == '{"task_id":"x"}'
    assert tokens == 9889 + 1200


def test_claude_read_tool_and_bash(bundle):
    rc = bundle / "incidents" / "root-cause.md"
    nm = bundle / "metrics" / "net-margin.md"
    text = "\n".join(json.dumps(e) for e in [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "let me read"},
            {"type": "tool_use", "name": "Read", "input": {"file_path": str(rc)}},
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": f"sed -n 1,5p {nm}"}},
        ]}},
        {"type": "result", "subtype": "success",
         "result": '{"task_id":"x"}',
         "usage": {"input_tokens": 18, "output_tokens": 153,
                   "cache_read_input_tokens": 16285}},
    ])
    answer, tokens, seen = _emit("claude", text, bundle)
    assert seen == ["/incidents/root-cause.md", "/metrics/net-margin.md"]
    assert answer == '{"task_id":"x"}'
    # parity with the old wrapper: input + output only (no cache tokens).
    assert tokens == 18 + 153


def test_reads_outside_bundle_are_dropped(bundle):
    text = json.dumps({"type": "item.completed", "item": {
        "type": "command_execution",
        "command": "/bin/bash -lc 'cat /etc/passwd /tmp/notes.md'", "exit_code": 0}})
    _, _, seen = _emit("codex", text, bundle)
    assert seen == []  # neither path is inside the bundle


def test_cwd_relative_paths_resolve(bundle, monkeypatch):
    """opencode/codex may emit paths relative to the agent cwd (project root)."""
    # Simulate the agent cwd being the bundle's parent (like the project root
    # with --dir pointing there); reads come in as 'bundlename/incidents/...'.
    monkeypatch.chdir(bundle.parent)
    relpath = f"{bundle.name}/incidents/root-cause.md"
    text = json.dumps({"type": "tool_use", "part": {"tool": "read", "state": {
        "input": {"filePath": relpath}}}})
    _, _, seen = _emit("opencode", text, bundle)
    assert seen == ["/incidents/root-cause.md"]


def test_directory_reads_are_dropped(bundle):
    """opencode's `read` tool accepts directories; those are not file reads."""
    text = "\n".join(json.dumps(e) for e in [
        {"type": "tool_use", "part": {"tool": "read", "state": {
            "input": {"filePath": str(bundle / "incidents")}}}},
        {"type": "tool_use", "part": {"tool": "read", "state": {
            "input": {"filePath": str(bundle / "incidents" / "root-cause.md")}}}},
    ])
    _, _, seen = _emit("opencode", text, bundle)
    assert seen == ["/incidents/root-cause.md"]


def test_glob_patterns_in_commands_are_skipped(bundle):
    """`cat *.md` is a glob, not a concrete file read."""
    text = "\n".join(json.dumps(e) for e in [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": f"cat {bundle}/incidents/*.md"}},
        ]}},
        {"type": "result", "result": "{}", "usage": {
            "input_tokens": 1, "output_tokens": 1}},
    ])
    _, _, seen = _emit("claude", text, bundle)
    assert seen == []


def test_duplicate_reads_are_deduped(bundle):
    rc = bundle / "incidents" / "root-cause.md"
    text = "\n".join(json.dumps(e) for e in [
        {"type": "tool_use", "part": {"tool": "read", "state": {
            "input": {"filePath": str(rc)}}}},
        {"type": "tool_use", "part": {"tool": "read", "state": {
            "input": {"filePath": str(rc)}}}},
    ])
    _, _, seen = _emit("opencode", text, bundle)
    assert seen == ["/incidents/root-cause.md"]


def test_markers_written_to_stderr(bundle, capsys):
    rc = bundle / "incidents" / "root-cause.md"
    emitter = tfe.TraceEmitter("claude", tfe._bundle_root())
    emitter.add_file(str(rc))
    captured = capsys.readouterr()
    line = captured.err.strip()
    assert line.startswith("OKF_TRACE: ")
    payload = json.loads(line[len("OKF_TRACE: "):])
    assert payload == {"type": "read", "path": "/incidents/root-cause.md",
                       "source": "claude"}
