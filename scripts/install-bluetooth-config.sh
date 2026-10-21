#!/usr/bin/env bash
# Install the stored Bluetooth autosuspend workaround; do not reload hardware.
# CONFIG_SYSTEM_ROOT redirects copies/backups for isolated checks.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target_root="${CONFIG_SYSTEM_ROOT:-/}"
mode="${1:-install}"
case "$mode" in install|--dry-run|--check) ;; *) echo "Usage: $0 [--dry-run|--check]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || { echo 'Expected at most one argument' >&2; exit 2; }
[[ "$target_root" == /* ]] || { echo 'CONFIG_SYSTEM_ROOT must be absolute' >&2; exit 2; }
sources=(system/modprobe.d/btusb-no-autosuspend.conf system/udev/51-btusb-no-autosuspend.rules)
destinations=(etc/modprobe.d/btusb-no-autosuspend.conf etc/udev/rules.d/51-btusb-no-autosuspend.rules)
for source in "${sources[@]}"; do
  [[ -f "$repo_root/$source" ]] || { echo "Missing source: $source" >&2; exit 1; }
done
if [[ "$mode" == install && "$target_root" == / && "$EUID" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
backup_root=""
failures=0
for index in "${!sources[@]}"; do
  src="$repo_root/${sources[$index]}"
  rel="${destinations[$index]}"
  dst="$target_root/$rel"
  if [[ ! -L "$dst" ]] && cmp -s -- "$src" "$dst"; then continue; fi
  case "$mode" in
    --dry-run) echo "COPY $src -> $dst (back up existing destination)"; continue ;;
    --check) echo "MISSING or different file: $dst"; failures=$((failures + 1)); continue ;;
  esac
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ -z "$backup_root" ]]; then
      mkdir -p -- "$target_root/var/backups/config-bluetooth"
      backup_root="$(mktemp -d "$target_root/var/backups/config-bluetooth/$(date +%Y%m%d-%H%M%S)-XXXXXX")"
    fi
    mkdir -p -- "$backup_root/$(dirname -- "$rel")"
    mv -- "$dst" "$backup_root/$rel"
  fi
  install -D -m 644 -- "$src" "$dst"
  echo "COPY $src -> $dst"
done
[[ -z "$backup_root" ]] || echo "Previous files: $backup_root"
exit "$((failures > 0))"
