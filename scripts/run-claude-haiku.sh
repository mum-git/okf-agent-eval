#!/bin/bash
export XDG_DATA_HOME=/tmp
export XDG_STATE_HOME=/tmp
prompt=$(cat)
exec /home/ben/.local/bin/claude --print --model haiku --dangerously-skip-permissions "$prompt"
