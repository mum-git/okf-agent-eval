#!/usr/bin/env python3
"""llama.cpp server agent wrapper for OKF benchmarks.

The runner prompt gives an external command only paths, not file contents. This
wrapper adds a small retrieval step so local OpenAI-compatible models can act as
file-reading agents: it reads a focused set of OKF files, injects them into the
model prompt, and writes runtime read events for the benchmark trace.
"""

from __future__ import annotations

import argparse
import os
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
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


SYSTEM_PROMPT = """You are an evaluation agent. Follow the user's benchmark prompt exactly.
Return exactly two JSON objects and no markdown fences, commentary, or prose.
The first object is the submission. The second object is the trace.
Use only facts found in the provided OKF file contents.
"""

STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "bundle",
    "but",
    "can",
    "citations",
    "closings",
    "enterprise",
    "file",
    "financial",
    "for",
    "from",
    "into",
    "its",
    "json",
    "must",
    "need",
    "object",
    "only",
    "path",
    "produce",
    "provide",
    "schema",
    "synthetic",
    "task",
    "that",
    "the",
    "this",
    "title",
    "two",
    "under",
    "use",
    "was",
    "were",
    "with",
    "you",
}

CONFLICT_TOKEN_GROUPS = (
    {"florida", "california", "texas", "new_york", "arizona", "nevada"},
    {"purchase", "refinance", "refi"},
    {"escrow", "claims", "mortgage", "tax", "lien"},
)

RUNNER_FIELDS = {
    "bundle": re.compile(r"^Bundle path:\s*(.+)$", re.MULTILINE),
    "task": re.compile(r"^Task path:\s*(.+)$", re.MULTILINE),
    "variant": re.compile(r"^Bundle variant:\s*(.+)$", re.MULTILINE),
}


def _request_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"llama.cpp server returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to reach llama.cpp server: {exc}") from exc


def _extract_runner_context(prompt: str) -> dict[str, str]:
    context: dict[str, str] = {}
    for key, pattern in RUNNER_FIELDS.items():
        match = pattern.search(prompt)
        if match:
            context[key] = match.group(1).strip()
    context.setdefault("bundle", os.environ.get("OKF_BUNDLE_PATH", ""))
    context.setdefault("task", os.environ.get("OKF_TASK_PATH", ""))
    context.setdefault("variant", os.environ.get("OKF_BUNDLE_VARIANT", ""))
    return {key: value for key, value in context.items() if value}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]


def _read_text(path: Path, max_chars: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n\n[truncated]\n"
    return text


def _bundle_relative(bundle: Path, path: Path) -> str:
    return "/" + path.relative_to(bundle).as_posix()


def _candidate_markdown_files(bundle: Path) -> list[Path]:
    return sorted(
        path for path in bundle.rglob("*.md")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(bundle).parts)
    )


def _path_score(rel_path: str, query_counts: Counter[str]) -> float:
    path_tokens = Counter(_tokenize(rel_path.replace("/", " ").replace("-", " ")))
    score = 0.0
    for token, query_weight in query_counts.items():
        if token in path_tokens:
            score += 8.0 * query_weight * path_tokens[token]
    if {"fnf", "fidelity"} & set(query_counts) and not (
        rel_path == "/index.md" or rel_path.startswith("/enterprise-fnf/")
    ):
        score -= 50.0
    query_tokens = set(query_counts)
    for group in CONFLICT_TOKEN_GROUPS:
        active = group & query_tokens
        if not active:
            continue
        conflicts = (group - active) & set(path_tokens)
        score -= 35.0 * len(conflicts)
    if rel_path.endswith("/index.md"):
        score *= 0.9
    return score


def _parse_index_hints(text: str) -> tuple[str, float]:
    """Extract task_hint/routing_hint text and priority multiplier from index frontmatter.

    Returns ("", 1.0) when there is no frontmatter (strict bundles).
    """
    if not text.startswith("---\n"):
        return "", 1.0
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", 1.0
    raw = text[4:end]
    hints: list[str] = []
    priority_mult = 1.0
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("task_hint:"):
            hints.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("routing_hint:"):
            hints.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("priority_hint:"):
            priority_mult = 2.5
    return " ".join(hints), priority_mult


def _content_score(text: str, query_counts: Counter[str]) -> float:
    tokens = Counter(_tokenize(text[:12000]))
    score = 0.0
    for token, query_weight in query_counts.items():
        count = tokens.get(token, 0)
        if count:
            score += min(count, 6) * query_weight
    return score


def _pick_index_files(
    bundle: Path,
    files: list[Path],
    query_counts: Counter[str],
    max_index_files: int,
) -> list[Path]:
    indexes = [path for path in files if path.name == "index.md"]
    selected: list[Path] = []
    for rel in ("/index.md", "/enterprise-fnf/index.md"):
        candidate = bundle / rel.lstrip("/")
        if candidate in indexes and candidate not in selected:
            selected.append(candidate)
    ranked = sorted(
        indexes,
        key=lambda path: (
            _path_score(_bundle_relative(bundle, path), query_counts),
            -len(path.parts),
            _bundle_relative(bundle, path),
        ),
        reverse=True,
    )
    for path in ranked:
        if len(selected) >= max_index_files:
            break
        if path not in selected:
            selected.append(path)
    return selected[:max_index_files]


def _ancestor_boost(path: Path, index_scores: dict[Path, float]) -> float:
    score = 0.0
    for directory, index_score in index_scores.items():
        try:
            path.relative_to(directory)
        except ValueError:
            continue
        # Closer indexes should matter more than broad parent indexes.
        distance = len(path.relative_to(directory).parts)
        score += index_score / max(distance, 1)
    return score


def _pick_content_files(
    bundle: Path,
    files: list[Path],
    query_counts: Counter[str],
    index_scores: dict[Path, float],
    max_content_files: int,
    task: dict[str, Any],
    use_required_citations: bool,
) -> list[Path]:
    selected: list[Path] = []
    if use_required_citations:
        for citation in task.get("required_citations", []):
            if not isinstance(citation, str):
                continue
            path = bundle / citation.lstrip("/")
            if path in files and path not in selected:
                selected.append(path)
                if len(selected) >= max_content_files:
                    return selected

    non_indexes = [path for path in files if path.name != "index.md"]
    ranked = sorted(
        non_indexes,
        key=lambda path: (
            _path_score(_bundle_relative(bundle, path), query_counts)
            + _ancestor_boost(path, index_scores),
            -len(path.parts),
            _bundle_relative(bundle, path),
        ),
        reverse=True,
    )
    for path in ranked:
        if len(selected) >= max_content_files:
            break
        if path not in selected:
            selected.append(path)
    return selected


def _write_trace_events(events: list[dict[str, Any]]) -> None:
    log_path = os.environ.get("OKF_TRACE_LOG")
    if not log_path or not events:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def _build_retrieved_prompt(
    prompt: str,
    *,
    max_files: int | None,
    max_index_files: int,
    max_chars_per_file: int,
    no_retrieval: bool,
    use_required_citations: bool,
    use_index_metadata: bool,
) -> tuple[str, list[dict[str, Any]]]:
    if no_retrieval:
        return prompt, []

    context = _extract_runner_context(prompt)
    bundle_raw = context.get("bundle")
    task_raw = context.get("task")
    if not bundle_raw or not task_raw:
        return prompt, []

    bundle = Path(bundle_raw).resolve()
    task_path = Path(task_raw).resolve()
    if not bundle.is_dir() or not task_path.is_file():
        return prompt, []

    task = json.loads(task_path.read_text(encoding="utf-8"))
    task_prompt = str(task.get("prompt") or "")
    task_id = str(task.get("task_id") or "")
    fact_keys = list((task.get("expected_facts") or {}).keys())
    query_counts = Counter(_tokenize(" ".join([task_id, task_prompt])))
    if not query_counts:
        query_counts = Counter(_tokenize(prompt))

    files = _candidate_markdown_files(bundle)
    target_max_files = max_files
    if target_max_files is None:
        trace_expectations = task.get("trace_expectations") or {}
        dynamic_max = trace_expectations.get("max_unique_files_read")
        target_max_files = dynamic_max if isinstance(dynamic_max, int) and dynamic_max > 0 else 22
    target_max_files = max(target_max_files, 1)

    index_budget = min(max(max_index_files, 0), max(target_max_files - 1, 0))
    indexes = _pick_index_files(bundle, files, query_counts, index_budget)
    index_texts: dict[Path, str] = {
        path: _read_text(path, max_chars_per_file)
        for path in indexes
    }
    index_scores: dict[Path, float] = {}
    for path, text in index_texts.items():
        if use_index_metadata:
            hint_text, priority_mult = _parse_index_hints(text)
            scoring_text = (text + " " + hint_text) if hint_text else text
        else:
            scoring_text, priority_mult = text, 1.0
        index_scores[path.parent] = _content_score(scoring_text, query_counts) * priority_mult
    content_budget = target_max_files - len(indexes)
    content_files = _pick_content_files(
        bundle,
        files,
        query_counts,
        index_scores,
        content_budget,
        task,
        use_required_citations,
    )

    selected = indexes + [path for path in content_files if path not in indexes]
    file_blocks: list[str] = []
    events: list[dict[str, Any]] = []
    for path in selected:
        rel_path = _bundle_relative(bundle, path)
        text = index_texts.get(path)
        if text is None:
            text = _read_text(path, max_chars_per_file)
        file_blocks.append(f"### {rel_path}\n{text.rstrip()}")
        events.append({"type": "read", "path": rel_path, "source": "llama_cpp_agent"})

    trace_paths = [event["path"] for event in events]
    augmented = f"""{prompt.rstrip()}

Resolved task:
- task_id: {task_id}
- bundle_variant: {context.get("variant", "")}
- task_prompt: {task_prompt}
- required fact keys: {json.dumps(fact_keys)}

Retrieved OKF file contents follow. Use only these contents for factual claims.
Do not infer from the grading fields in the task JSON; they are not provided here.
For the trace object, list file-read events for only these retrieved paths:
{json.dumps(trace_paths, indent=2)}

RETRIEVED OKF FILES

{chr(10).join(file_blocks)}
"""
    return augmented, events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_DEFAULTS),
        default="instruct",
        help="Sampling preset. Use instruct for this benchmark by default.",
    )
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-s", type=float, default=600)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--min-p", type=float)
    parser.add_argument("--presence-penalty", type=float)
    parser.add_argument("--repeat-penalty", type=float)
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum OKF markdown files to inject. Defaults to task trace max or 22.",
    )
    parser.add_argument(
        "--max-index-files",
        type=int,
        default=8,
        help="Maximum index.md files to read before selecting content files.",
    )
    parser.add_argument("--max-chars-per-file", type=int, default=6000)
    parser.add_argument("--no-retrieval", action="store_true")
    parser.add_argument(
        "--no-index-metadata",
        action="store_true",
        help="Ignore task_hint/routing_hint/priority_hint in index frontmatter when ranking files.",
    )
    parser.add_argument(
        "--use-required-citations",
        action="store_true",
        help="Debug/upper-bound mode: seed retrieval with grader citation paths.",
    )
    args = parser.parse_args()

    prompt = sys.stdin.read()
    if not prompt.strip():
        raise SystemExit("no prompt received on stdin")
    prompt, trace_events = _build_retrieved_prompt(
        prompt,
        max_files=args.max_files,
        max_index_files=args.max_index_files,
        max_chars_per_file=args.max_chars_per_file,
        no_retrieval=args.no_retrieval,
        use_required_citations=args.use_required_citations,
        use_index_metadata=not args.no_index_metadata,
    )
    _write_trace_events(trace_events)

    sampling = dict(MODE_DEFAULTS[args.mode])
    overrides = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "min_p": args.min_p,
        "presence_penalty": args.presence_penalty,
        "repeat_penalty": args.repeat_penalty,
    }
    for key, value in overrides.items():
        if value is not None:
            sampling[key] = value

    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": args.max_tokens,
        **sampling,
    }
    response = _request_json(
        args.base_url.rstrip("/") + "/chat/completions",
        payload,
        args.timeout_s,
    )
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"unexpected llama.cpp response shape: {json.dumps(response)[:1000]}") from exc
    print(content.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
