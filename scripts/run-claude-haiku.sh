#!/bin/bash
set -o pipefail
# Fresh-context Claude Code agent on haiku — OKF baseline.
# Clean room: fresh CLAUDE_CONFIG_DIR (credentials only, no plugins/settings),
# --disable-slash-commands (no skills), --print (no carried context).
# stream-json emits the native event stream; trace_from_events.py recovers the
# real reads (Read tool file_path + Bash commands) so trace_source becomes
# runtime-log instead of the model's self-report, and extracts tokens.
# stdout: agent's two JSON objects.  stderr: OKF_TRACE markers + "tokens used: N".
export XDG_DATA_HOME=/tmp XDG_STATE_HOME=/tmp

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
