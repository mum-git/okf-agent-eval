#!/bin/bash
# Baseline: llama.cpp tool agent navigating the OKF bundle via read_file only.
# Usage: echo "prompt" | run-llama-okf.sh
exec python3 /home/ben/okf-agent-eval/llama_cpp_tool_agent.py \
  --base-url http://127.0.0.1:1234/v1 \
  --model local-model \
  --mode instruct
