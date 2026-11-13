#!/usr/bin/env bash
set -euo pipefail

if [[ $(hostname -s) != homelab-dev || $(id -un) != humunkulud ]]; then
  echo 'Run as humunkulud on homelab-dev.' >&2
  exit 1
fi
mode=${1:-install}
if [[ $# -gt 1 || ( $mode != install && $mode != --check ) ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
relative=systemd/user/app-t3code.slice.d/50-homelab-memory.conf
destination="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/app-t3code.slice.d/50-homelab-memory.conf"
if [[ $mode == install ]]; then
  install -Dm644 "$repo/$relative" "$destination"
  systemctl --user daemon-reload
fi
cmp "$repo/$relative" "$destination"
[[ $(systemctl --user show app-t3code.slice -p MemoryHigh --value) == 15032385536 ]]
[[ $(systemctl --user show app-t3code.slice -p MemoryMax --value) == 17179869184 ]]
echo 'T3 agent parent slice: 14 GiB memory high, 16 GiB maximum; no service restart.'
