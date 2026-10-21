#!/usr/bin/env bash
set -euo pipefail

bridge="$HOME/Projects/thunderbird-mcp/mcp-bridge.cjs"
[[ -f "$bridge" ]] || { echo "Clone TKasperczyk/thunderbird-mcp into ~/Projects/thunderbird-mcp first." >&2; exit 1; }

# Expand HOME when Codex starts the bridge, so the registration works on either machine.
# shellcheck disable=SC2016
codex mcp add thunderbird -- sh -c 'exec node "$HOME/Projects/thunderbird-mcp/mcp-bridge.cjs"'
