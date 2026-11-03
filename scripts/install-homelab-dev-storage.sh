#!/usr/bin/env bash
# Install mounts after copying and verifying the worktrees on the new disk.
# This deliberately does not format disks, migrate files, or remove originals.
set -euo pipefail
[[ $(hostname -s) == homelab-dev && $(id -un) == humunkulud ]]
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$repo/systemd/homelab-dev"
target=/home/humunkulud/.t3/worktrees
[[ $(findmnt --noheadings --raw --output LABEL --mountpoint /srv/development) == dev-worktrees ]]
[[ -d /srv/development/worktrees && -d "$target" ]]
if ! mountpoint --quiet "$target"; then
  [[ -z $(ls -A -- "$target") ]] || {
    echo "Refusing to hide existing files at $target; finish the migration first." >&2
    exit 1
  }
else
  [[ $(findmnt --noheadings --raw --output LABEL --mountpoint "$target") == dev-worktrees ]]
  [[ $(findmnt --noheadings --raw --output FSROOT --mountpoint "$target") == /worktrees ]]
fi
for unit in srv-development.mount home-humunkulud-.t3-worktrees.mount; do
  sudo install -m 644 "$source_dir/$unit" "/etc/systemd/system/$unit"
done
install -d -m 755 "$HOME/.config/systemd/user/t3code.service.d"
install -m 644 "$source_dir/t3code-worktrees.conf" "$HOME/.config/systemd/user/t3code.service.d/worktrees.conf"
sudo systemctl daemon-reload
sudo systemctl enable --now srv-development.mount home-humunkulud-.t3-worktrees.mount
systemctl --user daemon-reload
mountpoint --quiet "$target"
findmnt --mountpoint "$target"
