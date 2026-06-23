#!/bin/bash
# Full haiku batch at 15 iterations with ground-truth (runtime-log) traces
# from trace_from_events.py.
#   4 canary levels (L1/L2/L3/L4) x 2 modes (okf/pg) x 15 iters = 120 runs.
# L1-L3 stress navigation DEPTH; L4 (atlas) stresses BREADTH (~181 decoy files).
# Sequential (--jobs 1) so duration measurements stay clean.
set -u
cd /home/ben/okf-agent-eval

# Re-seed the clean-room Claude config from the live credentials so the run
# starts with a fresh, valid OAuth token (avoids stale-token 401s).
rm -rf /tmp/claude-fresh-cfg

ITERS=15
declare -A PUB=(
  [L1]=tasks/concept-frontmatter-canary.public.json
  [L2]=tasks/deep-canary-l2.public.json
  [L3]=tasks/deep-canary-l3.public.json
  [L4]=tasks/deep-canary-l4.public.json
)
declare -A PRIV=(
  [L1]=tasks/concept-frontmatter-canary.json
  [L2]=tasks/deep-canary-l2.json
  [L3]=tasks/deep-canary-l3.json
  [L4]=tasks/deep-canary-l4.json
)
declare -A WRAP=(
  [okf]=./scripts/run-claude-haiku.sh
  [pg]=./scripts/run-claude-haiku-postgres.sh
)

for L in L1 L2 L3 L4; do
  for MODE in okf pg; do
    BID="haiku15-${L}-${MODE}"
    echo "===== $(date -u +%H:%M:%S) START $BID ====="
    rm -rf "runs/$BID"
    python3 batch_runner.py \
      --variants concept-real-yaml-minimal \
      --iterations "$ITERS" \
      --task "${PUB[$L]}" \
      --grade-task "${PRIV[$L]}" \
      --agent-cmd "${WRAP[$MODE]}" \
      --output-dir runs \
      --batch-id "$BID" \
      --jobs 1 \
      --timeout-s 300 \
      || echo "!!!!! $BID exited nonzero ($?) !!!!!"
    echo "===== $(date -u +%H:%M:%S) DONE  $BID ====="
  done
done
echo "===== $(date -u +%H:%M:%S) MATRIX COMPLETE ====="
