#!/usr/bin/env bash
# fix-greetd-hypr-lua.sh — DMS greeter: use Hyprland Lua (not deprecated .conf)
# and hide Hyprland (uwsm-managed) when uwsm is not installed.
#
# Needs sudo. Idempotent.
# Usage: ~/Documents/config/scripts/fix-greetd-hypr-lua.sh
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src_dir="$repo_root/system/greetd"

info() { printf '[INFO]  %s\n' "$*"; }
ok()   { printf '[OK]    %s\n' "$*"; }
warn() { printf '[WARN]  %s\n' "$*"; }

if [[ ! -f "$src_dir/dms-hypr.lua" || ! -f "$src_dir/config.toml" ]]; then
  printf 'Missing %s/{dms-hypr.lua,config.toml}\n' "$src_dir" >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

install -d -m 755 /etc/greetd
install -m 644 "$src_dir/dms-hypr.lua" /etc/greetd/dms-hypr.lua

if [[ -f /etc/greetd/config.toml ]]; then
  cp -a /etc/greetd/config.toml "/etc/greetd/config.toml.backup-$(date +%Y%m%d-%H%M%S)"
fi
install -m 644 "$src_dir/config.toml" /etc/greetd/config.toml
ok "Installed /etc/greetd/dms-hypr.lua + config.toml (Lua greeter compositor)"

uwsm_desktop=/usr/share/wayland-sessions/hyprland-uwsm.desktop
if [[ -f "$uwsm_desktop" ]]; then
  if command -v uwsm >/dev/null 2>&1; then
    info "uwsm is installed — leaving $uwsm_desktop"
  else
    mv "$uwsm_desktop" "${uwsm_desktop}.disabled"
    ok "Hid Hyprland (uwsm-managed) — uwsm not installed (DMS greeter ignores TryExec)"
    warn "hyprland package upgrades may restore it; re-run this script"
  fi
elif [[ -f "${uwsm_desktop}.disabled" ]]; then
  ok "uwsm session already disabled"
fi

ok "Done. Next greeter start uses Lua (log out or: systemctl restart greetd)"
