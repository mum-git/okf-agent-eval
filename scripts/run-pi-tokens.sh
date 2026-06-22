#!/bin/bash
# Runner that calls llama-server directly and reports token usage to stderr.
# Usage: echo "prompt" | run-pi-tokens.sh
# stdout: model response text
# stderr: "tokens used: N" (parsed by agent_runner.py)

exec python3 /home/ben/okf-agent-eval/scripts/run_llama_tokens.py
