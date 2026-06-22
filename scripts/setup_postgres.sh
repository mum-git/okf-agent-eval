#!/bin/bash
# Start the bundled PostgreSQL (pgserver) and apply the OKF schema.
# Idempotent: safe to run repeatedly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.pgvenv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: $PY not found. Create it with:" >&2
  echo "  python3.12 -m venv .pgvenv && .pgvenv/bin/pip install pgserver 'psycopg[binary]'" >&2
  exit 1
fi

echo "==> Ensuring cluster is running and database exists"
"$PY" "$ROOT/scripts/pg_common.py"

echo "==> Applying schema"
"$PY" - "$ROOT/scripts/schema.sql" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent) if False else "scripts")
# pg_common is importable because cwd is the project root
sys.path.insert(0, "scripts")
import pg_common

schema_sql = Path(sys.argv[1]).read_text()
with pg_common.connect() as conn:
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()
print("schema applied")
PY

echo "==> Done. Connection string:"
"$PY" -c "import sys; sys.path.insert(0,'scripts'); import pg_common; print(pg_common.conninfo())"
