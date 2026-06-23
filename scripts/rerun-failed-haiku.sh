#!/bin/bash
# Re-run only the haiku cells that failed due to the usage-limit cap
# (L3-pg, L4-okf, L4-pg) — the other 5 cells are clean 15/15 and untouched.
set -u
cd /home/ben/okf-agent-eval
rm -rf /tmp/claude-fresh-cfg   # re-seed clean-room creds with a fresh token

run_cell() {
  local BID="$1" PUB="$2" PRIV="$3" WRAP="$4"
  echo "===== $(date -u +%H:%M:%S) START $BID ====="
  rm -rf "runs/$BID"
  python3 batch_runner.py \
    --variants concept-real-yaml-minimal \
    --iterations 15 \
    --task "$PUB" \
    --grade-task "$PRIV" \
    --agent-cmd "$WRAP" \
    --output-dir runs \
    --batch-id "$BID" \
    --jobs 1 \
    --timeout-s 300 \
    || echo "!!!!! $BID exited nonzero ($?) !!!!!"
  echo "===== $(date -u +%H:%M:%S) DONE  $BID ====="
}

run_cell haiku15-L3-pg  tasks/deep-canary-l3.public.json tasks/deep-canary-l3.json ./scripts/run-claude-haiku-postgres.sh
run_cell haiku15-L4-okf tasks/deep-canary-l4.public.json tasks/deep-canary-l4.json ./scripts/run-claude-haiku.sh
run_cell haiku15-L4-pg  tasks/deep-canary-l4.public.json tasks/deep-canary-l4.json ./scripts/run-claude-haiku-postgres.sh
echo "===== $(date -u +%H:%M:%S) RERUN COMPLETE ====="
