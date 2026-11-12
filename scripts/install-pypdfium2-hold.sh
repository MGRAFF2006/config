#!/usr/bin/env bash
# Persist the single-package workaround without replacing pacman's configuration.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$repo_root/system/pacman/pypdfium2-hold.conf"
destination=/etc/pacman.d/pypdfium2-hold.conf
include="Include = $destination"
mode="${1:-install}"
case "$mode" in install|--dry-run|--check) ;; *) echo "Usage: $0 [--dry-run|--check]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || { echo 'Expected at most one argument' >&2; exit 2; }

if [[ "$mode" == --dry-run ]]; then
  echo "Install $destination and add its Include under [options] in /etc/pacman.conf."
  echo 'Hold only python-pypdfium2; preserve all other settings and install no packages.'
  exit
fi
if [[ "$mode" == --check ]]; then
  cmp -s -- "$source_file" "$destination"
  pacman-conf IgnorePkg | tr ' ' '\n' | grep -Fxq python-pypdfium2
  echo 'PASS: pacman and yay persistently hold python-pypdfium2.'
  exit
fi
[[ $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

# Refuse an unexpected layout instead of appending an option inside a repository.
[[ "$(grep -Fxc '[options]' /etc/pacman.conf)" == 1 ]]
mkdir -p /var/backups/config-pypdfium2-hold
backup="$(mktemp -d "/var/backups/config-pypdfium2-hold/$(date +%Y-%m-%d)-XXXXXXXX")"
cp -a -- /etc/pacman.conf "$backup/pacman.conf"
if [[ -e "$destination" || -L "$destination" ]]; then
  cp -a -- "$destination" "$backup/pypdfium2-hold.conf"
fi
install -D -m 644 -- "$source_file" "$destination"
if ! grep -Fxq "$include" /etc/pacman.conf; then
  sed -i '\|^\[options\]$|a Include = /etc/pacman.d/pypdfium2-hold.conf' /etc/pacman.conf
fi
echo "Previous configuration: $backup"
bash "$0" --check
