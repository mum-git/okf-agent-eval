#!/usr/bin/env python3
"""Query the postgres retrieval layer for OKF bundle chunks.

This is the single interface all three harnesses use to reach the DB:
  - codex / opencode shell out to the CLI form
  - llama_cpp_tool_agent's search_bundle tool also shells out to this CLI

Run under the project venv:
    .pgvenv/bin/python scripts/okf_search.py --variant <v> --query "..." [opts]

Every returned chunk carries its real bundle-relative file_path, so the agent
still cites real OKF files. When OKF_TRACE_LOG is set, each returned path is
appended as a `read` event (source: postgres-layer) so the grader counts these
as honest file accesses — postgres reads are NOT free in the trace.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pg_common  # noqa: E402


def okf_search(
    variant: str,
    query: str | None = None,
    file_type: str | None = None,
    required_keys: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """Return ranked bundle chunks matching the criteria.

    Each result: {file_path, file_type, file_depth, frontmatter_text, rank}.
    """
    where = ["bundle_variant = %(variant)s"]
    params: dict = {"variant": variant, "limit": limit}

    if file_type:
        where.append("file_type = %(file_type)s")
        params["file_type"] = file_type
    if required_keys:
        where.append("frontmatter_keys @> %(keys)s")
        params["keys"] = required_keys

    if query:
        where.append("search_tsv @@ websearch_to_tsquery('english', %(query)s)")
        params["query"] = query
        rank_expr = "ts_rank(search_tsv, websearch_to_tsquery('english', %(query)s))"
        order = f"{rank_expr} DESC, file_depth ASC"
        rank_select = rank_expr
    else:
        # No free-text query: rank by shallowest first (cheapest to reach).
        order = "file_depth ASC, file_path ASC"
        rank_select = "0.0"

    sql = f"""
        SELECT file_path, file_type, file_depth, frontmatter_text,
               {rank_select} AS rank
        FROM bundle_chunks
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT %(limit)s
    """

    with pg_common.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    for row in rows:
        if isinstance(row.get("rank"), float):
            row["rank"] = round(row["rank"], 4)
    return rows


def _emit_trace(paths: list[str]) -> None:
    log_path = os.environ.get("OKF_TRACE_LOG")
    if not log_path or not paths:
        return
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for path in paths:
            fh.write(json.dumps(
                {"type": "read", "path": path, "source": "postgres-layer"},
                sort_keys=True,
            ) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--query")
    parser.add_argument("--type", dest="file_type")
    parser.add_argument("--keys", help="comma-separated frontmatter keys to require")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--emit-trace", action="store_true",
                        help="Append returned paths to OKF_TRACE_LOG as read events.")
    parser.add_argument("--with-content", action="store_true",
                        help="Include frontmatter_text in output (default: yes).")
    parser.add_argument("--paths-only", action="store_true",
                        help="Output only file paths, one per line.")
    args = parser.parse_args()

    keys = [k.strip() for k in args.keys.split(",")] if args.keys else None
    results = okf_search(
        variant=args.variant,
        query=args.query,
        file_type=args.file_type,
        required_keys=keys,
        limit=args.limit,
    )

    if args.emit_trace:
        _emit_trace([r["file_path"] for r in results])

    if args.paths_only:
        for r in results:
            print(r["file_path"])
    else:
        print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
