#!/bin/bash
# Codex + local llama-server (Qwen3.6-27B) WITH the postgres retrieval layer.
# OKF_MODE=postgres triggers the search-command addendum in agent_runner.py.
# Usage: echo "prompt" | run-codex-postgres.sh
export OKF_MODE=postgres

codex exec \
  -p llamacpp \
  --oss \
  --model Qwen3.6-27B-Q5_K_M.gguf \
  --ephemeral \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  "$(cat)"
