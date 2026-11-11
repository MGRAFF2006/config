#!/usr/bin/env bash
set -euo pipefail
# Add one private path; leave other Tailscale Serve handlers untouched.
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$HOME/.config/systemd/user"
ln -sfn "$repo/systemd/user/agent-morning-dashboard.service" "$HOME/.config/systemd/user/agent-morning-dashboard.service"
systemctl --user daemon-reload
systemctl --user enable --now agent-morning-dashboard.service
tailscale serve --bg --set-path=/morning http://127.0.0.1:8787
