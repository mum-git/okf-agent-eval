#!/bin/bash
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
export OPENCODE_HOME=/home/ben/.config/opencode
prompt=$(cat)
exec /home/ben/.opencode/bin/opencode run --model local/Qwen3.6-27B-Q5_K_M.gguf --dir /home/ben/okf-agent-eval --dangerously-skip-permissions "$prompt"
