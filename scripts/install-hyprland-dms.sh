#!/usr/bin/env bash
# Install the optional session. PAM/greeter changes require --with-greeter (laptop).
# Usage: bash scripts/install-hyprland-dms.sh laptop|desktop [--dry-run] [--with-greeter] [--with-appearance]
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
machine=""
dry_run=false
with_greeter=false
with_appearance=false
for arg in "$@"; do
  case "$arg" in
    laptop|desktop) [[ -z "$machine" ]] || exit 2; machine="$arg" ;;
    --dry-run) dry_run=true ;;
    --with-greeter) with_greeter=true ;;
    --with-appearance) with_appearance=true ;;
    *) echo "Usage: $0 laptop|desktop [--dry-run] [--with-greeter] [--with-appearance]" >&2; exit 2 ;;
  esac
done
[[ -n "$machine" ]] || { echo 'Specify laptop or desktop' >&2; exit 2; }
if "$with_greeter" && [[ "$machine" != laptop ]]; then
  echo 'The managed Howdy/PAM stack is specific to the laptop camera; use the existing desktop login manager' >&2
  exit 2
fi
target_home="${CONFIG_LINK_HOME:-$HOME}"
state_dir="${CONFIG_DEPLOY_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/config}"
manifest="$state_dir/hyprland-dms-packages.txt"
mapfile -t native < <(awk '{sub(/#.*/, ""); if (NF) print $1}' "$repo_root/packages/hyprland-dms.txt")
mapfile -t aur < <(awk '{sub(/#.*/, ""); if (NF) print $1}' "$repo_root/packages/aur-hyprland-dms.txt")
if "$with_greeter"; then aur+=(howdy-git); fi
bash "$repo_root/scripts/link-home.sh" "$machine" --dry-run >/dev/null
if "$dry_run"; then
  printf 'Official packages: %s\nAUR packages: %s\n' "${native[*]}" "${aur[*]}"
  printf 'Initialize missing DMS settings; link %s config. PAM/greeter changes: %s\n' "$machine" "$with_greeter"
  printf 'Apply saved desktop and application appearance: %s\n' "$with_appearance"
  exit 0
fi
command -v yay >/dev/null || { echo 'Install yay first, or run the workstation installer' >&2; exit 1; }
installed_before="$(pacman -Qq)"
# Record only requested packages absent before this setup. Pre-existing packages
# belong to the workstation, including shared Plasma utilities.
mkdir -p -- "$state_dir"
temporary="$(mktemp "$state_dir/hyprland-dms-XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
{
  if [[ -f "$manifest" ]]; then cat "$manifest"; fi
  for package in "${native[@]}" "${aur[@]}"; do
    if ! grep -Fxq "$package" <<< "$installed_before"; then printf '%s\n' "$package"; fi
  done
} | LC_ALL=C sort -u > "$temporary"
mv -- "$temporary" "$manifest"
sudo pacman -Syu --needed --noconfirm "${native[@]}"
yay -S --needed --noconfirm "${aur[@]}"
bash "$repo_root/scripts/link-home.sh" "$machine"
XDG_CONFIG_HOME="$target_home/.config" python3 "$repo_root/scripts/configure-dms-bar-panels.py" --init
XDG_CONFIG_HOME="$target_home/.config" python3 "$repo_root/scripts/configure-dms-app-integration.py"
if "$with_appearance"; then
  XDG_CONFIG_HOME="$target_home/.config" python3 "$repo_root/scripts/configure-desktop-appearance.py" --apply
  XDG_CONFIG_HOME="$target_home/.config" python3 "$repo_root/scripts/configure-desktop-app-themes.py" --apply
fi
# Disable future systemd autostart under Plasma, without stopping a running shell.
systemctl --user disable dms.service
systemctl --user daemon-reload
if "$with_greeter"; then
  bash "$repo_root/scripts/fix-greetd-hypr-lua.sh"
  bash "$repo_root/scripts/install-pam-keyring-howdy.sh"
  if [[ -f "$target_home/.config/dms/settings.json" && -f "$target_home/.local/state/dms/session.json" && -f "$target_home/.cache/dms/dms-colors.json" ]]; then
    python3 "$repo_root/scripts/install-dms-greeter-theme.py" --apply
  else
    systemctl --user enable --now dms-greeter-settings-permissions.path
    systemctl --user enable dms-greeter-settings-permissions.service
    echo 'After the first DMS login, run scripts/install-dms-greeter-theme.py --apply for the guarded login-screen appearance.'
  fi
  echo 'Managed PAM and greetd files installed; review the greeter guide before changing the active login manager.'
fi
printf 'Hyprland/DMS configured. Select Hyprland at your existing login manager.\n'
printf 'New package record: %s\nRollback: bash scripts/remove-hyprland-dms.sh --dry-run\n' "$manifest"
