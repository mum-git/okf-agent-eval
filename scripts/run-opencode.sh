#!/bin/bash
set -o pipefail
# opencode against the local model. --format json emits the native event
# stream; trace_from_events.py recovers the real reads (opencode `read` tool
# filePath + `bash` commands) so trace_source becomes runtime-log instead of
# the model's self-report.
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
export OPENCODE_HOME=/home/ben/.config/opencode
ADAPTER=/home/ben/okf-agent-eval/scripts/trace_from_events.py
prompt=$(cat)
/home/ben/.opencode/bin/opencode run \
  --model local/Qwen3.6-27B-Q5_K_M.gguf \
  --dir /home/ben/okf-agent-eval \
  --dangerously-skip-permissions \
  --format json \
  "$prompt" \
  | python3 "$ADAPTER" --format opencode --source opencode
