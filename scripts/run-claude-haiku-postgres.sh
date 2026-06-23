#!/bin/bash
set -o pipefail
# Fresh-context Claude Code agent on haiku — WITH postgres retrieval layer.
# Clean room: fresh CLAUDE_CONFIG_DIR (credentials only, no plugins/settings),
# --disable-slash-commands (no skills), --print (no carried context).
# stream-json + trace_from_events.py recovers Claude's native reads; the
# okf_search.py calls additionally log their reads to OKF_TRACE_LOG, so the
# merged trace covers both the search layer and any native file reads.
# stdout: agent's two JSON objects.  stderr: OKF_TRACE markers + "tokens used: N".
export XDG_DATA_HOME=/tmp XDG_STATE_HOME=/tmp
export OKF_MODE=postgres

FRESH=/tmp/claude-fresh-cfg
if [ ! -f "$FRESH/.credentials.json" ]; then
  mkdir -p "$FRESH"
  cp "$HOME/.claude/.credentials.json" "$FRESH/" 2>/dev/null
fi
export CLAUDE_CONFIG_DIR="$FRESH"
ADAPTER=/home/ben/okf-agent-eval/scripts/trace_from_events.py

prompt=$(cat)
/home/ben/.local/bin/claude --print --output-format stream-json --verbose --model haiku \
  --dangerously-skip-permissions --disable-slash-commands "$prompt" \
  | python3 "$ADAPTER" --format claude --source claude
