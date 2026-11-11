#!/usr/bin/env bash
set -euo pipefail
umask 077
export PATH="$HOME/.local/bin:$PATH"
command -v codex >/dev/null || { echo 'Morning brief cannot find Codex; install its existing homelab launcher in ~/.local/bin.' >&2; exit 1; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
state="$HOME/.local/state/agent-life"
mkdir -p "$state/briefs"
exec 9> "$state/brief.lock"
flock -n 9 || { echo 'A morning brief is already running.' >&2; exit 1; }
node "$repo/scripts/agent-life.cjs" collect
day=$(TZ=Europe/Berlin date +%F)
temporary="$state/briefs/$day.pending.md"
cd "$state"
# Synthesis gets data, no command execution, personal MCP clients or web search.
codex exec --json --ignore-user-config --ephemeral --sandbox read-only --skip-git-repo-check \
    -c 'features.shell_tool=false' -c 'web_search="disabled"' -c 'approval_policy="never"' \
    -o "$temporary" - < "$state/brief-prompt.txt" > "$state/brief-run.log" 2>&1
[[ -s $temporary ]] || { echo 'Brief generation returned no summary; previous briefs retained.' >&2; exit 1; }
mv -- "$temporary" "$state/briefs/$day.md"
cp -- "$state/briefs/$day.md" "$state/latest-brief.md.pending"
mv -- "$state/latest-brief.md.pending" "$state/latest-brief.md"
node "$repo/scripts/agent-morning-dashboard.cjs" publish
printf 'Morning brief ready for %s (Europe/Berlin).\n' "$day"
