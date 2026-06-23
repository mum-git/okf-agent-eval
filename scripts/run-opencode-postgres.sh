#!/bin/bash
set -o pipefail
# opencode + local model, WITH the postgres retrieval layer.
# OKF_MODE=postgres triggers the search-command addendum in agent_runner.py.
# --format json + trace_from_events.py recovers opencode's native reads; the
# okf_search.py calls additionally log their reads to OKF_TRACE_LOG, so the
# merged trace covers both the search layer and any native file reads.
# Usage: echo "prompt" | run-opencode-postgres.sh
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
export OPENCODE_HOME=/home/ben/.config/opencode
export OKF_MODE=postgres
ADAPTER=/home/ben/okf-agent-eval/scripts/trace_from_events.py
prompt=$(cat)
/home/ben/.opencode/bin/opencode run \
  --model local/Qwen3.6-27B-Q5_K_M.gguf \
  --dir /home/ben/okf-agent-eval \
  --dangerously-skip-permissions \
  --format json \
  "$prompt" \
  | python3 "$ADAPTER" --format opencode --source opencode
