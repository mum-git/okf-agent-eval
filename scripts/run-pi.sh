#!/bin/bash
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
export PI_CODING_AGENT_DIR=/home/ben/.pi/agent
prompt=$(cat)
exec /home/ben/.hermes/node/bin/pi --print --no-session --model lmstudio/Qwen3.6-27B-Q5_K_M "$prompt"
