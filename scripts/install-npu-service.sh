#!/usr/bin/env bash
# Install a per-account system service so NPU memlock needs no session changes.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:---dry-run}"
account="${2:-${SUDO_USER:-$USER}}"
case "$mode" in --dry-run|--check|--apply) ;; *) echo "Usage: $0 [--dry-run|--check|--apply] [account]" >&2; exit 2 ;; esac
[[ $# -le 2 ]] || { echo 'Expected at most two arguments' >&2; exit 2; }
[[ "$account" =~ ^[a-z_][a-z0-9_-]*$ && "$account" != root ]] || { echo 'Expected a non-root account name' >&2; exit 2; }
account_home="$(getent passwd "$account" | cut -d: -f6)"
[[ "$account_home" == "/home/$account" ]] || { echo "Service requires /home/$account; found $account_home" >&2; exit 1; }
source_file="$repo_root/systemd/flm@.service"
destination=/etc/systemd/system/flm@.service
if [[ "$mode" == --check ]]; then
  cmp -- "$source_file" "$destination"
  systemctl is-enabled "flm@$account.service"
  systemctl is-active "flm@$account.service"
  exit
fi
if [[ "$mode" == --dry-run ]]; then
  echo "Install $source_file -> $destination (back up an existing different unit)"
  echo "Enable and restart flm@$account.service; NPU API: http://127.0.0.1:52625/v1"
  exit
fi
[[ "$EUID" -eq 0 ]] || exec sudo bash "$0" "$mode" "$account"
command -v flm >/dev/null
[[ -d "$account_home/.config/flm" ]] || install -d -o "$account" -g "$(id -gn "$account")" -m 700 "$account_home/.config/flm"
if [[ -e "$destination" || -L "$destination" ]]; then
  if ! cmp -s -- "$source_file" "$destination"; then
    backup_dir="$(mktemp -d /var/backups/config-npu-XXXXXXXX)"
    cp -a -- "$destination" "$backup_dir/"
    echo "Previous unit: $backup_dir"
  fi
fi
install -m 644 -- "$source_file" "$destination"
systemctl daemon-reload
if systemctl is-failed --quiet "flm@$account.service"; then
  systemctl reset-failed "flm@$account.service"
fi
systemctl enable "flm@$account.service"
systemctl restart "flm@$account.service"
