#!/bin/bash
# opencode (local Qwen3.6-27B-UD-Q4_K_XL via llama-server :1234) OKF vs postgres,
# across all 5 canary levels, 5 iterations each = 5 x 2 x 5 = 50 runs.
# Ground-truth runtime-log traces via trace_from_events.py. Sequential for clean
# timing. Note: the server ignores the wrapper's --model string and serves the
# single loaded model (UD-Q4_K_XL).
set -u
cd /home/ben/okf-agent-eval

ITERS=5
declare -A PUB=(
  [L1]=tasks/concept-frontmatter-canary.public.json
  [L2]=tasks/deep-canary-l2.public.json
  [L3]=tasks/deep-canary-l3.public.json
  [L4]=tasks/deep-canary-l4.public.json
  [L5]=tasks/deep-canary-l5.public.json
)
declare -A PRIV=(
  [L1]=tasks/concept-frontmatter-canary.json
  [L2]=tasks/deep-canary-l2.json
  [L3]=tasks/deep-canary-l3.json
  [L4]=tasks/deep-canary-l4.json
  [L5]=tasks/deep-canary-l5.json
)
declare -A WRAP=(
  [okf]=./scripts/run-opencode.sh
  [pg]=./scripts/run-opencode-postgres.sh
)

for L in L1 L2 L3 L4 L5; do
  for MODE in okf pg; do
    BID="oc5-${L}-${MODE}"
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
      --timeout-s 400 \
      || echo "!!!!! $BID exited nonzero ($?) !!!!!"
    echo "===== $(date -u +%H:%M:%S) DONE  $BID ====="
  done
done
echo "===== $(date -u +%H:%M:%S) OC5 COMPLETE ====="
