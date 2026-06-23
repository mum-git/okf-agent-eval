#!/usr/bin/env python3
"""Convert a CLI harness's native event stream into benchmark trace markers.

The OKF baseline wrappers (codex/opencode/claude) used to emit only the model's
self-reported trace JSON, so trace scoring trusted the model's word about which
files it read. This adapter reads each harness's *native* event stream on stdin
and recovers the real reads:

  - prints canonical ``OKF_TRACE: {"type":"read","path":...}`` markers to stderr
    (ingested by agent_runner._read_runtime_events -> trace_source="runtime-log"),
  - prints the harness's final answer text to stdout (the two JSON objects the
    model produced, which agent_runner parses for the submission/trace),
  - prints ``tokens used: N`` to stderr for agent_runner._extract_tokens_used.

Read paths are emitted bundle-relative (beginning with "/"), matching the llama
tool agent and the grader's expectations. The bundle root is taken from
OKF_BUNDLE_PATH (set by agent_runner).

Formats (verified against the installed CLIs):
  codex    `codex exec --json`            JSONL; reads are command_execution
                                          items whose `command` shells out to
                                          cat/sed; answer is an agent_message
                                          item; usage on turn.completed.
  opencode `opencode run --format json`   JSONL parts; read tool ->
                                          part.state.input.filePath, bash ->
                                          part.state.input.command; answer is
                                          text parts; usage on step_finish.
  claude   `claude --output-format        JSONL; assistant.message.content[]
            stream-json --verbose`        tool_use blocks (Read.file_path,
                                          Bash.command); answer + usage on the
                                          final result event.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


# A shell command may read several files (e.g. `cat a.md b.md`). Pull out every
# token that looks like a path to a markdown file, with or without surrounding
# quotes. Only .md paths count as content reads (an `ls dir` is not a read).
_MD_PATH_RE = re.compile(r"""['"]?((?:/|\.{0,2}/)?[^\s'"|;&><]+\.md)['"]?""")


def _bundle_root() -> Path | None:
    raw = os.environ.get("OKF_BUNDLE_PATH")
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except OSError:
        return None


def _to_bundle_relative(path_str: str, bundle: Path | None) -> str | None:
    """Return a "/"-prefixed bundle-relative path, or None if outside the bundle."""
    if not path_str:
        return None
    cleaned = path_str.strip().strip("'\"")
    if not cleaned:
        return None
    candidate = Path(cleaned)
    if bundle is not None:
        bundle = bundle.resolve()
        if candidate.is_absolute():
            bases = [candidate]
        else:
            # Harnesses emit paths relative to different roots: opencode/codex
            # often use the agent cwd (the project root, where --dir points),
            # others use a path already relative to the bundle. Try both.
            bases = [Path.cwd() / cleaned, bundle / cleaned]
        for resolved in bases:
            try:
                rel = resolved.resolve().relative_to(bundle)
                return "/" + str(rel)
            except (ValueError, OSError):
                continue
        return None
    # No bundle context: accept already-relative-looking markdown paths as-is.
    if cleaned.endswith(".md"):
        return "/" + cleaned.lstrip("/")
    return None


def _paths_from_command(command: str, bundle: Path | None) -> list[str]:
    out: list[str] = []
    for match in _MD_PATH_RE.finditer(command or ""):
        token = match.group(1)
        # A glob (cat *.md, head incidents/*.md) is not a concrete file read.
        if any(ch in token for ch in "*?[]"):
            continue
        rel = _to_bundle_relative(token, bundle)
        if rel:
            out.append(rel)
    return out


class TraceEmitter:
    """Collects deduped read events and writes canonical markers to stderr."""

    def __init__(self, source: str, bundle: Path | None) -> None:
        self.source = source
        self.bundle = bundle
        self._seen: set[str] = set()

    def add_file(self, path_str: str | None) -> None:
        rel = _to_bundle_relative(path_str or "", self.bundle)
        self._emit(rel)

    def add_command(self, command: str | None) -> None:
        for rel in _paths_from_command(command or "", self.bundle):
            self._emit(rel)

    def _emit(self, rel: str | None) -> None:
        # Bundles are entirely markdown; a directory read (opencode's `read`
        # tool accepts directories) is navigation, not a file read. Restrict to
        # .md so trace events match the grader's domain and the llama agent's
        # read_file semantics.
        if not rel or not rel.endswith(".md") or rel in self._seen:
            return
        self._seen.add(rel)
        marker = {"type": "read", "path": rel, "source": self.source}
        print("OKF_TRACE: " + json.dumps(marker, sort_keys=True), file=sys.stderr)

    @property
    def count(self) -> int:
        return len(self._seen)


def _iter_json_lines(text: str) -> Iterable[dict[str, Any]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


# ---------------------------------------------------------------------------
# Per-harness parsers. Each returns (final_answer_text, tokens_used|None) and
# emits read markers via the emitter as a side effect.
# ---------------------------------------------------------------------------

def parse_codex(text: str, emitter: TraceEmitter) -> tuple[str, int | None]:
    answer = ""
    tokens = 0
    saw_usage = False
    for obj in _iter_json_lines(text):
        kind = obj.get("type", "")
        if kind in ("item.completed", "item.started"):
            item = obj.get("item") or {}
            if item.get("type") == "command_execution":
                emitter.add_command(item.get("command"))
            elif item.get("type") == "agent_message" and kind == "item.completed":
                answer = item.get("text") or answer
        elif kind == "turn.completed":
            usage = obj.get("usage") or {}
            inp = usage.get("input_tokens") or 0
            out = usage.get("output_tokens") or 0
            if inp or out:
                tokens += int(inp) + int(out)
                saw_usage = True
    return answer, (tokens if saw_usage else None)


def parse_opencode(text: str, emitter: TraceEmitter) -> tuple[str, int | None]:
    answer_parts: list[str] = []
    tokens = 0
    saw_usage = False
    for obj in _iter_json_lines(text):
        kind = obj.get("type", "")
        part = obj.get("part") or {}
        if kind == "tool_use":
            tool = part.get("tool")
            state_input = ((part.get("state") or {}).get("input")) or {}
            if tool == "read":
                emitter.add_file(state_input.get("filePath"))
            elif tool == "bash":
                emitter.add_command(state_input.get("command"))
        elif kind == "text":
            txt = part.get("text")
            if txt:
                answer_parts.append(txt)
        elif kind == "step_finish":
            total = (part.get("tokens") or {}).get("total")
            if isinstance(total, (int, float)) and total:
                tokens += int(total)
                saw_usage = True
    return "\n".join(answer_parts), (tokens if saw_usage else None)


def parse_claude(text: str, emitter: TraceEmitter) -> tuple[str, int | None]:
    answer = ""
    tokens: int | None = None
    for obj in _iter_json_lines(text):
        kind = obj.get("type", "")
        if kind == "assistant":
            for block in (obj.get("message") or {}).get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = (block.get("name") or "").lower()
                tool_input = block.get("input") or {}
                if name == "read":
                    emitter.add_file(tool_input.get("file_path"))
                elif name == "bash":
                    emitter.add_command(tool_input.get("command"))
        elif kind == "result":
            answer = obj.get("result") or answer
            usage = obj.get("usage") or {}
            inp = usage.get("input_tokens")
            out = usage.get("output_tokens")
            if inp is not None or out is not None:
                tokens = int(inp or 0) + int(out or 0)
    return answer, tokens


PARSERS = {
    "codex": parse_codex,
    "opencode": parse_opencode,
    "claude": parse_claude,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", required=True, choices=sorted(PARSERS))
    parser.add_argument(
        "--source",
        help="trace event source label (defaults to the format name)",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()
    bundle = _bundle_root()
    emitter = TraceEmitter(args.source or args.format, bundle)
    answer, tokens = PARSERS[args.format](raw, emitter)

    sys.stdout.write(answer if answer.endswith("\n") or not answer else answer + "\n")
    if tokens is not None:
        print(f"tokens used: {tokens}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
