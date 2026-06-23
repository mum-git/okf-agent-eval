#!/bin/bash
set -o pipefail
# Codex against the local llama-server (Qwen3.6-27B on :1234) via the
# `llamacpp` profile, which sets [oss] base_url = http://127.0.0.1:1234/v1.
# --json emits the native event stream; trace_from_events.py recovers the real
# file reads (codex reads via shell cat/sed) so trace_source becomes
# runtime-log instead of the model's self-report.
# Usage: echo "prompt" | run-codex-local.sh
ADAPTER=/home/ben/okf-agent-eval/scripts/trace_from_events.py
prompt=$(cat)

codex exec \
  -p llamacpp \
  --oss \
  --model Qwen3.6-27B-Q5_K_M.gguf \
  --ephemeral \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$prompt" \
  | python3 "$ADAPTER" --format codex --source codex
