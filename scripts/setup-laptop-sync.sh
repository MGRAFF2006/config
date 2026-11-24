#!/usr/bin/env bash
# Reduce laptop scan bursts without changing synced files or restarting Syncthing.
set -euo pipefail

machine="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["HostName"])')"
[[ "$machine" == laptop ]] || { echo "This tuning is only for laptop, got: $machine" >&2; exit 1; }

folders="$(syncthing cli config folders list)"
[[ -n "$folders" ]] || { echo 'No Syncthing folders configured' >&2; exit 1; }

# Save only the settings being changed; credentials and full config stay local.
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/config"
mkdir -p -- "$state_dir"
backup="$(mktemp "$state_dir/laptop-sync-before-$(date +%F)-XXXXXX.sh")"
chmod 600 "$backup"
printf '#!/usr/bin/env bash\nset -euo pipefail\n' > "$backup"
previous="$(syncthing cli config options raw-max-folder-concurrency get)"
printf 'syncthing cli config options raw-max-folder-concurrency set %q\n' "$previous" >> "$backup"
while IFS= read -r folder; do
  previous="$(syncthing cli config folders "$folder" hashers get)"
  printf 'syncthing cli config folders %q hashers set %q\n' "$folder" "$previous" >> "$backup"
done <<< "$folders"

echo "Restore previous settings: bash $backup"
syncthing cli config options raw-max-folder-concurrency set 1
while IFS= read -r folder; do
  syncthing cli config folders "$folder" hashers set 1
done <<< "$folders"
echo 'Applied: one folder scan/sync at a time, one hasher per folder.'
