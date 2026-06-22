#!/bin/bash
# Fresh-context Claude Code agent on haiku — WITH postgres retrieval layer.
# Clean room: fresh CLAUDE_CONFIG_DIR (credentials only, no plugins/settings),
# --disable-slash-commands (no skills), --print (no carried context).
# stdout: agent's two JSON objects.  stderr: "tokens used: N".
export XDG_DATA_HOME=/tmp XDG_STATE_HOME=/tmp

FRESH=/tmp/claude-fresh-cfg
if [ ! -f "$FRESH/.credentials.json" ]; then
  mkdir -p "$FRESH"
  cp "$HOME/.claude/.credentials.json" "$FRESH/" 2>/dev/null
fi
export CLAUDE_CONFIG_DIR="$FRESH"

prompt=$(cat)
out=$(/home/ben/.local/bin/claude --print --output-format json --model haiku \
  --dangerously-skip-permissions --disable-slash-commands "$prompt")
echo "$out" | jq -r '.result'
echo "$out" | jq -r '"tokens used: " + ((.usage.input_tokens + .usage.output_tokens)|tostring)' >&2
