#!/bin/bash
set -o pipefail
# Codex + local llama-server (Qwen3.6-27B) WITH the postgres retrieval layer.
# OKF_MODE=postgres triggers the search-command addendum in agent_runner.py.
# --json + trace_from_events.py recovers codex's native shell reads; the
# okf_search.py calls additionally log their reads to OKF_TRACE_LOG, so the
# merged trace covers both the search layer and any native file reads.
# Usage: echo "prompt" | run-codex-postgres.sh
export OKF_MODE=postgres
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
