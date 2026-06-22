#!/bin/bash
# Codex against the local llama-server (Qwen3.6-27B on :1234) via the
# `llamacpp` profile, which sets [oss] base_url = http://127.0.0.1:1234/v1.
# Usage: echo "prompt" | run-codex-local.sh

codex exec \
  -p llamacpp \
  --oss \
  --model Qwen3.6-27B-Q5_K_M.gguf \
  --ephemeral \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  "$(cat)"
