#!/usr/bin/env bash
# install-hyprland-dms.sh — Additive Hyprland + DMS install (keeps Plasma / DWM)
# Usage: ~/Documents/config/scripts/install-hyprland-dms.sh
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pkg_file="$repo_root/packages/hyprland-dms.txt"

info() { printf '[INFO]  %s\n' "$*"; }
ok()   { printf '[OK]    %s\n' "$*"; }
warn() { printf '[WARN]  %s\n' "$*"; }

if [[ ! -f "$pkg_file" ]]; then
  printf 'Missing package list: %s\n' "$pkg_file" >&2
  exit 1
fi

info "Installing packages from $pkg_file (Plasma/DWM untouched)..."
mapfile -t packages < <(grep -vE '^\s*(#|$)' "$pkg_file")
sudo pacman -S --needed --noconfirm "${packages[@]}"
ok "Packages installed"

aur_file="$repo_root/packages/aur-laptop.txt"
if [[ -f "$aur_file" ]] && command -v yay &>/dev/null; then
  mapfile -t aur_packages < <(grep -vE '^\s*(#|$)' "$aur_file")
  if ((${#aur_packages[@]})); then
    info "Installing AUR companions from $aur_file..."
    yay -S --needed --noconfirm "${aur_packages[@]}"
    ok "AUR companions installed"
  fi
fi

info "Linking home configs..."
"$repo_root/scripts/link-home.sh"
ok "Configs linked"

if [[ -f "$HOME/.config/DankMaterialShell/settings.json" ]]; then
  # Quickshell atomically replaces settings.json, so preserve greeter access
  # for both the current file and future rewrites.
  setfacl -b "$HOME/.config/DankMaterialShell/settings.json"
  chgrp greeter "$HOME/.config/DankMaterialShell" "$HOME/.config/DankMaterialShell/settings.json"
  chmod g+s "$HOME/.config/DankMaterialShell"
  chmod g+r "$HOME/.config/DankMaterialShell/settings.json"

  info "Configuring dedicated DMS network/audio bar panels..."
  "$repo_root/scripts/configure-dms-bar-panels.py"
  ok "DMS bar panels configured"
else
  warn "DMS settings do not exist yet; run scripts/configure-dms-bar-panels.py after the first DMS start"
fi

info "Connecting Zen and Dolphin to the DMS theme/default-app setup..."
"$repo_root/scripts/configure-dms-app-integration.py"
ok "Desktop applications integrated"

info "Configuring greetd DMS greeter for Hyprland Lua (+ hide broken uwsm session)..."
"$repo_root/scripts/fix-greetd-hypr-lua.sh"
ok "greetd Hyprland Lua greeter config applied"

info "Installing Howdy + KWallet PAM stacks (greetd / SDDM / DMS lock)..."
"$repo_root/scripts/install-pam-keyring-howdy.sh"
ok "PAM stacks installed"

# Ensure DMS does not autostart under Plasma (WantedBy=graphical-session.target)
systemctl --user disable --now dms.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/graphical-session.target.wants/dms.service"
rm -f "$HOME/.config/systemd/user/hyprland-session.target.wants/dms.service"
systemctl --user daemon-reload
systemctl --user enable --now dms-greeter-settings-permissions.path
ok "dms.service left disabled — Hyprland starts it via 'dms run -d' in hyprland.lua"

info "Reloading user systemd for hyprland-session.target..."
systemctl --user daemon-reload
ok "hyprland-session.target available"

if command -v dms &>/dev/null; then
  info "Running dms doctor (informational)..."
  dms doctor || warn "dms doctor reported issues (ok before first Hyprland login)"
fi

cat <<'EOF'

Done. Reversible trial setup:

  1. Log out (Leave → Log out)
  2. At the DMS greeter, choose session "Hyprland" (Plasma remains listed)
  3. Log in — DMS starts via hyprland.lua (dms run -d)

Do not pick "Hyprland (uwsm-managed)" unless uwsm is installed — the install
script disables that entry when uwsm is missing.

Useful keys (also Super+Shift+/ for cheatsheet):
  Super+Space / Super+R  launcher
  Super+A                control center (WiFi/BT/audio)
  Super+T                terminal (Alacritty)
  Super+,                DMS settings
  Fn volume/brightness   via DMS OSD

Rollback anytime:
  - Log out → pick "Plasma" at the greeter
  - Or run: ~/Documents/config/scripts/remove-hyprland-dms.sh

EOF
