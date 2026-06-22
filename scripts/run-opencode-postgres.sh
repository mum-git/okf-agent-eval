#!/bin/bash
# opencode + local model, WITH the postgres retrieval layer.
# OKF_MODE=postgres triggers the search-command addendum in agent_runner.py.
# Usage: echo "prompt" | run-opencode-postgres.sh
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
export OPENCODE_HOME=/home/ben/.config/opencode
export OKF_MODE=postgres
prompt=$(cat)
exec /home/ben/.opencode/bin/opencode run \
  --model local/Qwen3.6-27B-Q5_K_M.gguf \
  --dir /home/ben/okf-agent-eval \
  --dangerously-skip-permissions \
  "$prompt"
