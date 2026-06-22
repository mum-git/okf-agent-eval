#!/bin/bash
# Postgres layer: llama.cpp tool agent with the search_bundle tool.
# Usage: echo "prompt" | run-llama-postgres.sh
exec python3 /home/ben/okf-agent-eval/llama_cpp_tool_agent_postgres.py \
  --base-url http://127.0.0.1:1234/v1 \
  --model local-model \
  --mode instruct
