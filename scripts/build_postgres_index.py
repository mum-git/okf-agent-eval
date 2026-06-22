#!/usr/bin/env python3
"""Index OKF bundle Markdown files into the postgres retrieval layer.

Run under the project venv:
    .pgvenv/bin/python scripts/build_postgres_index.py [--variants V1 V2 ...]

Each Markdown file becomes one row in bundle_chunks, keyed to its
bundle-relative path. The search_tsv column is weighted so frontmatter matches
rank above path matches, which rank above body matches. Idempotent UPSERT on
(bundle_variant, file_path).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pg_common  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Default: the top-performing variant. Pass --variants to widen.
DEFAULT_VARIANTS = ["concept-real-yaml-minimal"]

_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z0-9_.-]+):")


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body). Tolerant of files without frontmatter."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text  # malformed — treat whole file as body
    return text[4:end], text[end + 5 :]


def _frontmatter_keys(fm: str) -> list[str]:
    keys: list[str] = []
    for line in fm.splitlines():
        if line and not line.startswith((" ", "\t", "#", "-")):
            m = _TOP_LEVEL_KEY.match(line)
            if m:
                keys.append(m.group(1))
    return keys


def _field(fm: str, key: str) -> str | None:
    pat = re.compile(rf"^{re.escape(key)}:\s*(.+)$", re.MULTILINE)
    m = pat.search(fm)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


UPSERT = """
INSERT INTO bundle_chunks (
  bundle_variant, file_path, is_index, is_concept, file_type, file_depth,
  frontmatter_keys, frontmatter_text, body_text, search_tsv
) VALUES (
  %(variant)s, %(path)s, %(is_index)s, %(is_concept)s, %(file_type)s, %(depth)s,
  %(keys)s, %(fm)s, %(body)s,
  setweight(to_tsvector('english', coalesce(%(fm)s,'')), 'A') ||
  setweight(to_tsvector('english', coalesce(%(path_words)s,'')), 'B') ||
  setweight(to_tsvector('english', coalesce(%(body)s,'')), 'C')
)
ON CONFLICT (bundle_variant, file_path) DO UPDATE SET
  is_index = EXCLUDED.is_index,
  is_concept = EXCLUDED.is_concept,
  file_type = EXCLUDED.file_type,
  file_depth = EXCLUDED.file_depth,
  frontmatter_keys = EXCLUDED.frontmatter_keys,
  frontmatter_text = EXCLUDED.frontmatter_text,
  body_text = EXCLUDED.body_text,
  search_tsv = EXCLUDED.search_tsv;
"""


def index_variant(conn, variant: str) -> int:
    bundle = ROOT / "bundles" / f"{variant}-retail-ops"
    if not bundle.exists():
        print(f"  skip {variant} (bundle not found)")
        return 0
    count = 0
    with conn.cursor() as cur:
        for md in sorted(bundle.rglob("*.md")):
            rel = "/" + str(md.relative_to(bundle))
            text = md.read_text(encoding="utf-8", errors="replace")
            fm, body = _split_frontmatter(text)
            keys = _frontmatter_keys(fm)
            is_index = md.name == "index.md"
            file_type = _field(fm, "type")
            # path words: split on non-alphanumerics so full-text can match path tokens
            path_words = " ".join(re.split(r"[^A-Za-z0-9]+", rel))
            cur.execute(UPSERT, {
                "variant": variant,
                "path": rel,
                "is_index": is_index,
                "is_concept": (not is_index) and bool(fm or body.strip()),
                "file_type": file_type,
                "depth": rel.count("/"),
                "keys": keys,
                "fm": fm,
                "body": body,
                "path_words": path_words,
            })
            count += 1
    conn.commit()
    print(f"  ok   {variant}: {count} files")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    args = parser.parse_args()

    total = 0
    with pg_common.connect() as conn:
        for variant in args.variants:
            total += index_variant(conn, variant)
    print(f"\nIndexed {total} files across {len(args.variants)} variant(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
