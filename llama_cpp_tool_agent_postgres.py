#!/usr/bin/env python3
"""llama.cpp tool agent WITH a postgres retrieval-layer tool.

Identical to llama_cpp_tool_agent.py but exposes a second tool, `search_bundle`,
that queries the postgres index (via scripts/okf_search.py) to locate
answer-bearing files without walking the directory tree. The model still cites
the real bundle-relative paths the search returns, and every returned path is
logged as a `read` event (deduped, same machinery as read_file) so trace scoring
stays honest.

Reuses the base module's helpers so there is a single source of truth for the
HTTP loop, file reading, context extraction, and trace writing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import llama_cpp_tool_agent as base
from llama_cpp_tool_agent import (
    MODE_DEFAULTS,
    READ_FILE_TOOL,
    SYSTEM_PROMPT,
    _extract_context,
    _post,
    _read_file_tool,
    _usage_tokens,
    _write_trace,
)

ROOT = Path(__file__).resolve().parent
SEARCH_PY = ROOT / "scripts" / "okf_search.py"
SEARCH_PYTHON = ROOT / ".pgvenv" / "bin" / "python"

SEARCH_BUNDLE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_bundle",
        "description": (
            "Search a PostgreSQL index OVER the OKF bundle to find answer-bearing "
            "files fast, instead of walking the directory tree. Returns ranked "
            "chunks, each with its real bundle-relative file_path and its YAML "
            "frontmatter. You MUST cite the real file_path values returned. Use "
            "this to jump straight to root-cause, remediation, and registry files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text keywords, e.g. 'nexus root cause remediation'.",
                },
                "file_type": {
                    "type": "string",
                    "description": "Optional frontmatter type filter, e.g. root_cause, remediation, metric_registry.",
                },
                "required_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional frontmatter keys that must be present, e.g. ['incident_id','remediation'].",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5).",
                },
            },
            "required": ["query"],
        },
    },
}

POSTGRES_SYSTEM_SUFFIX = """

You ALSO have a search_bundle tool backed by a PostgreSQL index over this same
bundle. Prefer it to locate files quickly: one search can return the root-cause,
remediation, and registry files directly instead of reading many index files.
The search returns each file's real path and frontmatter — cite those real
paths. You may still use read_file to confirm a value.
"""


def _search_bundle_tool(variant: str, func_args: dict[str, Any]) -> tuple[str, list[str]]:
    """Run okf_search.py and return (json_text_for_model, [paths_found])."""
    cmd = [
        str(SEARCH_PYTHON), str(SEARCH_PY),
        "--variant", variant,
        "--limit", str(func_args.get("limit") or 5),
    ]
    query = func_args.get("query")
    if query:
        cmd += ["--query", str(query)]
    if func_args.get("file_type"):
        cmd += ["--type", str(func_args["file_type"])]
    keys = func_args.get("required_keys")
    if keys:
        cmd += ["--keys", ",".join(str(k) for k in keys)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: search failed: {exc}", []
    if proc.returncode != 0:
        return f"ERROR: search exited {proc.returncode}: {proc.stderr.strip()}", []
    try:
        results = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return f"ERROR: search returned non-JSON: {proc.stdout[:300]}", []
    paths = [r["file_path"] for r in results if r.get("file_path")]
    return proc.stdout, paths


def run(args: argparse.Namespace) -> int:
    runner_prompt = sys.stdin.read()
    if not runner_prompt.strip():
        raise SystemExit("no prompt on stdin")

    ctx = _extract_context(runner_prompt)
    bundle_raw = ctx.get("bundle")
    task_raw = ctx.get("task")
    variant = ctx.get("variant", "unknown")
    if not bundle_raw or not task_raw:
        raise SystemExit("could not extract Bundle path / Task path from prompt")

    bundle = Path(bundle_raw).resolve()
    task_path = Path(task_raw).resolve()
    if not bundle.is_dir():
        raise SystemExit(f"bundle not found: {bundle}")
    if not task_path.is_file():
        raise SystemExit(f"task file not found: {task_path}")

    task = json.loads(task_path.read_text(encoding="utf-8"))
    task_prompt = task.get("prompt", "")
    fact_keys = list((task.get("expected_facts") or {}).keys())

    user_message = (
        f"Bundle path: {bundle}\n"
        f"Bundle variant: {variant}\n\n"
        f"Task: {task_prompt}\n\n"
        f"Expected fact keys: {json.dumps(fact_keys)}\n\n"
        f"Start by using search_bundle to locate the relevant files."
    )

    sampling = dict(MODE_DEFAULTS[args.mode])
    for attr, key in [
        ("temperature", "temperature"), ("top_p", "top_p"), ("top_k", "top_k"),
        ("min_p", "min_p"), ("presence_penalty", "presence_penalty"),
        ("repeat_penalty", "repeat_penalty"),
    ]:
        val = getattr(args, attr.replace("-", "_"), None)
        if val is not None:
            sampling[key] = val

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + POSTGRES_SYSTEM_SUFFIX},
        {"role": "user", "content": user_message},
    ]

    trace_events: list[dict[str, Any]] = []
    files_read: set[str] = set()
    total_tokens = 0
    tools = [READ_FILE_TOOL, SEARCH_BUNDLE_TOOL]

    def _record(path: str, source: str) -> None:
        clean = ("/" + path.lstrip("/")) if path else path
        if clean and clean not in files_read:
            files_read.add(clean)
            trace_events.append({"type": "read", "path": clean, "source": source})

    for _ in range(args.max_iterations):
        payload: dict[str, Any] = {
            "model": args.model,
            "messages": messages,
            "max_tokens": args.max_tokens,
            "tools": tools,
            "tool_choice": "auto",
            **sampling,
        }
        response = _post(args.base_url.rstrip("/") + "/chat/completions", payload, args.timeout_s)
        total_tokens += _usage_tokens(response)
        try:
            choice = response["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SystemExit(f"unexpected response shape: {json.dumps(response)[:500]}") from exc

        messages.append({"role": "assistant", **{k: v for k, v in message.items() if k != "role"}})
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            print((message.get("content") or "").strip())
            print(f"tokens used: {total_tokens}", file=sys.stderr)
            _write_trace(trace_events)
            return 0

        for call in tool_calls:
            call_id = call.get("id", "")
            func = call.get("function", {})
            func_name = func.get("name", "")
            try:
                func_args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                func_args = {}

            if func_name == "read_file":
                path = func_args.get("path", "")
                content = _read_file_tool(bundle, path, args.max_chars_per_file)
                if not content.startswith("ERROR"):
                    _record(path, "llama-cpp-tool-agent")
            elif func_name == "search_bundle":
                content, paths = _search_bundle_tool(variant, func_args)
                for p in paths:
                    _record(p, "postgres-layer")
            else:
                content = f"ERROR: unknown tool {func_name!r}"

            messages.append({"role": "tool", "tool_call_id": call_id, "content": content})

    messages.append({
        "role": "user",
        "content": (
            "You have reached the tool-call limit. "
            "Produce the two JSON objects now using what you have read."
        ),
    })
    payload = {
        "model": args.model, "messages": messages,
        "max_tokens": args.max_tokens, **sampling,
    }
    response = _post(args.base_url.rstrip("/") + "/chat/completions", payload, args.timeout_s)
    total_tokens += _usage_tokens(response)
    try:
        content = response["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        content = ""
    print(content.strip())
    print(f"tokens used: {total_tokens}", file=sys.stderr)
    _write_trace(trace_events)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--mode", choices=sorted(MODE_DEFAULTS), default="instruct")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-s", type=float, default=600)
    parser.add_argument("--max-iterations", type=int, default=30)
    parser.add_argument("--max-chars-per-file", type=int, default=6000)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--min-p", type=float)
    parser.add_argument("--presence-penalty", type=float)
    parser.add_argument("--repeat-penalty", type=float)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
