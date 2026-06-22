#!/usr/bin/env python3
"""Tool-calling agent wrapper for llama.cpp OKF benchmarks.

Unlike llama_cpp_agent.py (which pre-injects files), this wrapper gives the
model a read_file tool and runs a multi-turn conversation loop. The model
decides what to read, the wrapper executes the file read and returns the
content, and the loop continues until the model stops calling tools and
produces its final answer — exactly how Claude Code or an Azure AI Foundry
function-tool agent behaves.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MODE_DEFAULTS = {
    "thinking-general": {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 0.0,
        "repeat_penalty": 1.0,
    },
    "thinking-coding": {
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 0.0,
        "repeat_penalty": 1.0,
    },
    "instruct": {
        "temperature": 0.7,
        "top_p": 0.80,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "repeat_penalty": 1.0,
    },
}

SYSTEM_PROMPT = """\
You are an evaluation agent investigating an OKF knowledge bundle.

You have a read_file tool. Use it to navigate the bundle interactively:
- Start by reading /index.md to understand the top-level structure.
- Follow links in index files to find relevant subdirectories.
- Read concept files that seem relevant to the task.

When you find an incident or root-cause file, do NOT stop there. You must \
also read every pipeline, schema, table, and business-segment file it \
references. Incident files summarise what went wrong; the pipeline and schema \
files contain the exact field names, join keys, and asset names required for \
precise answers.

For every fact that involves a key name, asset name, or pipeline name, your \
answer must use the exact identifier found in the relevant schema or pipeline \
file — not a paraphrase. When a fact asks for a bad key versus a correct key, \
state both: "X instead of Y".

Only stop reading when you have read the incident files AND the underlying \
pipeline/schema/table files they reference.

When you are done reading, output exactly two JSON objects with no markdown \
fences or prose:

1. Submission object:
{
  "task_id": "...",
  "bundle_variant": "...",
  "answer": "short synthesized answer",
  "facts": { <one key per expected fact> },
  "citations": ["/bundle-relative/paths/you/actually/read.md"]
}

2. Trace object:
{
  "agent": "llama-cpp-tool-agent",
  "bundle_variant": "...",
  "events": [{"type": "read", "path": "/..."}]
}

Use only facts found in files you actually read. Do not infer from prior \
knowledge.
"""

READ_FILE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Read a file from the OKF bundle by its bundle-relative path. "
            "Always start with /index.md, then follow links in index files to "
            "navigate to relevant subdirectories and concept files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Bundle-relative path beginning with /, "
                        "e.g. /index.md or /enterprise-fnf/incidents/index.md"
                    ),
                }
            },
            "required": ["path"],
        },
    },
}

RUNNER_FIELDS = {
    "bundle": re.compile(r"^Bundle path:\s*(.+)$", re.MULTILINE),
    "task":   re.compile(r"^Task path:\s*(.+)$", re.MULTILINE),
    "variant": re.compile(r"^Bundle variant:\s*(.+)$", re.MULTILINE),
}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"llama.cpp HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"cannot reach llama.cpp server: {exc}") from exc


# ---------------------------------------------------------------------------
# Bundle / task helpers
# ---------------------------------------------------------------------------

def _extract_context(prompt: str) -> dict[str, str]:
    ctx: dict[str, str] = {}
    for key, pat in RUNNER_FIELDS.items():
        m = pat.search(prompt)
        if m:
            ctx[key] = m.group(1).strip()
    ctx.setdefault("bundle", os.environ.get("OKF_BUNDLE_PATH", ""))
    ctx.setdefault("task",   os.environ.get("OKF_TASK_PATH", ""))
    ctx.setdefault("variant", os.environ.get("OKF_BUNDLE_VARIANT", ""))
    return {k: v for k, v in ctx.items() if v}


def _read_file_tool(bundle: Path, path: str, max_chars: int) -> str:
    """Execute a read_file tool call. Returns file content or an error string."""
    clean = path.strip()
    if not clean.startswith("/"):
        clean = "/" + clean
    # Resolve to absolute, then verify it lives inside the bundle.
    target = (bundle / clean.lstrip("/")).resolve()
    try:
        target.relative_to(bundle.resolve())
    except ValueError:
        return f"ERROR: path {path!r} is outside the bundle."
    if not target.exists():
        return f"ERROR: file not found: {clean}"
    if not target.is_file():
        return f"ERROR: not a file: {clean}"
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[truncated]\n"
    return text


def _usage_tokens(response: dict[str, Any]) -> int:
    """Total tokens reported in a chat/completions response (0 if absent).

    The server already computes this; reading it adds no model work or requests.
    """
    usage = response.get("usage") or {}
    try:
        return int(usage.get("total_tokens") or 0)
    except (TypeError, ValueError):
        return 0


def _write_trace(events: list[dict[str, Any]]) -> None:
    log_path = os.environ.get("OKF_TRACE_LOG")
    if not log_path or not events:
        return
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True) + "\n")


def _json_objects(text: str) -> list[Any]:
    decoder = json.JSONDecoder()
    out: list[Any] = []
    idx = 0
    while idx < len(text):
        candidates = [p for p in (text.find("{", idx), text.find("[", idx)) if p != -1]
        if not candidates:
            break
        start = min(candidates)
        try:
            obj, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue
        out.append(obj)
        idx = start + end
    return out


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    runner_prompt = sys.stdin.read()
    if not runner_prompt.strip():
        raise SystemExit("no prompt on stdin")

    ctx = _extract_context(runner_prompt)
    bundle_raw = ctx.get("bundle")
    task_raw   = ctx.get("task")
    variant    = ctx.get("variant", "unknown")

    if not bundle_raw or not task_raw:
        raise SystemExit("could not extract Bundle path / Task path from prompt")

    bundle    = Path(bundle_raw).resolve()
    task_path = Path(task_raw).resolve()

    if not bundle.is_dir():
        raise SystemExit(f"bundle not found: {bundle}")
    if not task_path.is_file():
        raise SystemExit(f"task file not found: {task_path}")

    task      = json.loads(task_path.read_text(encoding="utf-8"))
    task_id   = task.get("task_id", "")
    task_prompt = task.get("prompt", "")
    fact_keys = list((task.get("expected_facts") or {}).keys())

    user_message = (
        f"Bundle path: {bundle}\n"
        f"Bundle variant: {variant}\n\n"
        f"Task: {task_prompt}\n\n"
        f"Expected fact keys: {json.dumps(fact_keys)}\n\n"
        f"Start by reading /index.md."
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
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_message},
    ]

    trace_events: list[dict[str, Any]] = []
    files_read: set[str] = set()
    total_tokens = 0

    for iteration in range(args.max_iterations):
        payload: dict[str, Any] = {
            "model":      args.model,
            "messages":   messages,
            "max_tokens": args.max_tokens,
            "tools":      [READ_FILE_TOOL],
            "tool_choice": "auto",
            **sampling,
        }
        response = _post(
            args.base_url.rstrip("/") + "/chat/completions",
            payload,
            args.timeout_s,
        )
        total_tokens += _usage_tokens(response)

        try:
            choice  = response["choices"][0]
            message = choice["message"]
            finish  = choice.get("finish_reason", "")
        except (KeyError, IndexError, TypeError) as exc:
            raise SystemExit(f"unexpected response shape: {json.dumps(response)[:500]}") from exc

        # Append assistant turn to history.
        messages.append({"role": "assistant", **{
            k: v for k, v in message.items() if k != "role"
        }})

        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            # Model stopped calling tools — extract the final answer.
            content = (message.get("content") or "").strip()
            print(content)
            print(f"tokens used: {total_tokens}", file=sys.stderr)
            _write_trace(trace_events)
            return 0

        # Execute each tool call and append results.
        for call in tool_calls:
            call_id   = call.get("id", "")
            func      = call.get("function", {})
            func_name = func.get("name", "")
            try:
                func_args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                func_args = {}

            if func_name == "read_file":
                path = func_args.get("path", "")
                content = _read_file_tool(bundle, path, args.max_chars_per_file)
                # Normalise the path for the trace.
                clean_path = ("/" + path.lstrip("/")) if path else path
                if not content.startswith("ERROR") and clean_path not in files_read:
                    files_read.add(clean_path)
                    event: dict[str, Any] = {
                        "type": "read",
                        "path": clean_path,
                        "source": "llama-cpp-tool-agent",
                    }
                    trace_events.append(event)
            else:
                content = f"ERROR: unknown tool {func_name!r}"

            messages.append({
                "role":         "tool",
                "tool_call_id": call_id,
                "content":      content,
            })

    # Hit iteration limit — ask the model to produce its final answer now.
    messages.append({
        "role": "user",
        "content": (
            "You have reached the file-read limit. "
            "Produce the two JSON objects now using what you have read."
        ),
    })
    payload = {
        "model":      args.model,
        "messages":   messages,
        "max_tokens": args.max_tokens,
        **sampling,
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument(
        "--mode", choices=sorted(MODE_DEFAULTS), default="instruct",
    )
    parser.add_argument("--max-tokens",        type=int,   default=4096)
    parser.add_argument("--timeout-s",         type=float, default=600)
    parser.add_argument("--max-iterations",    type=int,   default=30,
                        help="Maximum read_file calls before forcing a final answer.")
    parser.add_argument("--max-chars-per-file", type=int,  default=6000)
    parser.add_argument("--temperature",       type=float)
    parser.add_argument("--top-p",             type=float)
    parser.add_argument("--top-k",             type=int)
    parser.add_argument("--min-p",             type=float)
    parser.add_argument("--presence-penalty",  type=float)
    parser.add_argument("--repeat-penalty",    type=float)
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
