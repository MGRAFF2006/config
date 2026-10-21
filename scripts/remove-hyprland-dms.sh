#!/usr/bin/env bash
# Remove only packages introduced by the recorded optional-session installation.
# User settings, links, credentials and PAM backups are retained.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-remove}"
case "$mode" in remove|--dry-run) ;; *) echo "Usage: $0 [--dry-run]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || exit 2
state_dir="${CONFIG_DEPLOY_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/config}"
manifest="$state_dir/hyprland-dms-packages.txt"
[[ -f "$manifest" ]] || {
  echo "No installation record at $manifest. Switch to Plasma/DWM for a soft rollback; select any package removals manually." >&2
  exit 1
}
installed="$(pacman -Qq)"
packages=()
while IFS= read -r package; do
  [[ -n "$package" ]] || continue
  [[ "$package" =~ ^[a-zA-Z0-9@._+:-]+$ ]] || { echo 'Invalid package record' >&2; exit 1; }
  if grep -Fxq "$package" <<< "$installed"; then packages+=("$package"); fi
done < "$manifest"
if [[ "$mode" == --dry-run ]]; then
  printf 'Packages introduced by this setup and still installed: %s\n' "${packages[*]:-none}"
  echo 'Settings and config links will be retained. Active Hyprland/greetd must be left before removing packages.'
  exit 0
fi
if [[ "${XDG_CURRENT_DESKTOP:-}" == *Hyprland* ]]; then
  echo 'Log into Plasma/DWM before removing the running compositor' >&2; exit 1
fi
if systemctl is-active --quiet greetd.service || systemctl is-enabled --quiet greetd.service; then
  echo 'Restore the fallback display manager and review the PAM backups before removing the active greeter' >&2; exit 1
fi
if ((${#packages[@]})); then
  sudo pacman -R --noconfirm "${packages[@]}"
fi
rm -f -- "$manifest"
echo "Recorded Hyprland/DMS packages removed. Configuration sources and local settings retained in $repo_root and your home."
