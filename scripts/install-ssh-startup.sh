#!/usr/bin/env bash
# Keep SSH's Tailscale readiness check out of multi-user.target's boot path.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$repo_root/system/ssh/sshd-tailscale.timer"
destination=/etc/systemd/system/sshd-tailscale.timer
mode="${1:-install}"
case "$mode" in install|--dry-run|--check) ;; *) echo "Usage: $0 [--dry-run|--check]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || { echo 'Expected at most one argument' >&2; exit 2; }

# This migration is only for the existing private, Tailscale-ordered sshd setup.
ordering="$(systemctl show sshd.service --property=After --value)"
[[ " $ordering " == *' tailscale-online.target '* ]] || {
  echo 'sshd.service must already wait for tailscale-online.target.' >&2
  exit 1
}
if [[ "$mode" == --dry-run ]]; then
  echo "Install $destination, enable its timer, and disable sshd.service's direct boot start."
  echo 'The running SSH daemon and its private listeners are preserved.'
  exit
fi
if [[ "$mode" == --check ]]; then
  cmp -s -- "$source_file" "$destination"
  systemctl is-enabled --quiet sshd-tailscale.timer
  systemctl is-active --quiet sshd-tailscale.timer
  [[ "$(systemctl is-enabled sshd.service || true)" == disabled ]]
  echo 'PASS: private SSH starts through its timer without blocking multi-user.target.'
  exit
fi
[[ $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

mkdir -p /var/backups/config-ssh-startup
backup="$(mktemp -d "/var/backups/config-ssh-startup/$(date +%Y-%m-%d)-XXXXXXXX")"
if [[ -e "$destination" || -L "$destination" ]]; then
  cp -a -- "$destination" "$backup/sshd-tailscale.timer"
fi
systemctl is-enabled sshd.service > "$backup/sshd-enabled.txt" || true
systemctl is-enabled sshd-tailscale.timer > "$backup/timer-enabled.txt" 2>/dev/null || true
install -D -m 644 -- "$source_file" "$destination"
systemctl daemon-reload
# Enable the replacement first. Do not stop or restart an existing SSH daemon.
systemctl enable --now sshd-tailscale.timer
systemctl disable sshd.service
echo "Previous timer and enablement states: $backup"
bash "$0" --check
