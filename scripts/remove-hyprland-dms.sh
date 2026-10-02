#!/usr/bin/env bash
# remove-hyprland-dms.sh — Remove Hyprland + DMS packages; leave Plasma / DWM alone
# Does not delete ~/Documents/config sources (only unlinks + removes packages).
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pkg_file="$repo_root/packages/hyprland-dms.txt"

info() { printf '[INFO]  %s\n' "$*"; }
ok()   { printf '[OK]    %s\n' "$*"; }

systemctl --user disable --now dms.service 2>/dev/null || true
systemctl --user disable --now dms-greeter-settings-permissions.path 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/hyprland-session.target.wants/dms.service"
rm -f "$HOME/.config/systemd/user/graphical-session.target.wants/dms.service"
systemctl --user daemon-reload || true
ok "Detached / disabled dms.service"

if [[ -f "$pkg_file" ]]; then
  mapfile -t wanted < <(grep -vE '^\s*(#|$)' "$pkg_file")
  mapfile -t installed < <(pacman -Qq "${wanted[@]}" 2>/dev/null || true)
  if ((${#installed[@]})); then
    info "Removing: ${installed[*]}"
    sudo pacman -Rns --noconfirm "${installed[@]}"
    ok "Packages removed"
  else
    info "No listed hyprland-dms packages installed"
  fi
fi

# Unlink hypr config if it points at the repo (optional cleanup)
for path in \
  "$HOME/.config/hypr" \
  "$HOME/.config/systemd/user/hyprland-session.target" \
  "$HOME/.config/systemd/user/dms-greeter-settings-permissions.service" \
  "$HOME/.config/systemd/user/dms-greeter-settings-permissions.path"
do
  if [[ -L "$path" ]]; then
    target="$(readlink -f "$path" || true)"
    if [[ "$target" == "$repo_root"/* ]]; then
      rm -f "$path"
      info "Unlinked $path"
    fi
  fi
done

# Optional DMS user state (settings/cache) — keep by default
if [[ "${REMOVE_DMS_STATE:-0}" == "1" ]]; then
  rm -rf "$HOME/.config/DankMaterialShell" \
    "$HOME/.local/state/DankMaterialShell" \
    "$HOME/.cache/DankMaterialShell"
  ok "Removed DMS user state"
else
  info "Kept DMS settings under ~/.config/DankMaterialShell (set REMOVE_DMS_STATE=1 to wipe)"
fi

cat <<'EOF'

Hyprland/DMS removed. Log into Plasma (laptop) or startx/dwm (desktop) as before.
Config sources remain in ~/Documents/config if you want to retry later.

EOF
