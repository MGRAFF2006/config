#!/usr/bin/env bash
# Link curated config only; package installation and service activation are separate.
# Usage: bash scripts/link-home.sh [laptop|desktop] [--dry-run|--check]
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
home_root="$repo_root/home"
target_home="${CONFIG_LINK_HOME:-$HOME}"
mode=install
machine=""
for arg in "$@"; do
  case "$arg" in
    laptop|desktop)
      [[ -z "$machine" ]] || { echo "Specify one machine" >&2; exit 2; }
      machine="$arg" ;;
    --dry-run|--check)
      [[ "$mode" == install ]] || { echo "Specify one mode" >&2; exit 2; }
      mode="$arg" ;;
    *) echo "Usage: $0 [laptop|desktop] [--dry-run|--check]" >&2; exit 2 ;;
  esac
done
if [[ -z "$machine" ]]; then
  machine="${MACHINE_TYPE:-}"
  if [[ -z "$machine" ]] && command -v tailscale >/dev/null 2>&1; then
    machine="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["HostName"])' 2>/dev/null || true)"
  fi
fi
case "$machine" in
  laptop|desktop) ;;
  *) echo "Pass laptop|desktop explicitly; Tailscale identity is unavailable or unsupported" >&2; exit 2 ;;
esac

links=(
  .zshrc .bashrc .gitconfig
  .config/zshrc .config/zshrc.d
  .config/environment.d/alicevision.conf
  .config/starship.toml .config/fastfetch .config/nvim
  .config/alacritty/alacritty.toml .config/alacritty/nordic.toml
  .local/bin/meshroom
  .local/share/applications/Meshroom.desktop
  .local/share/applications/nvim.desktop
  .local/share/applications/com.blackmagicdesign.resolve.desktop
  .config/hypr
  .config/wireplumber/wireplumber.conf.d/51-bt-hold-a2dp.conf
  .config/zen-browser/user.js .config/zen-browser/userContent.css
  .config/DankMaterialShell/theme_nord.json
  .config/DankMaterialShell/plugins/networkDiagnostics
  .local/bin/bt-a2dp-claim
  .config/systemd/user/bt-a2dp-claim.service
  .config/systemd/user/hyprland-session.target
  .config/systemd/user/hypr-kwallet.service
  .config/systemd/user/dms-greeter-settings-permissions.service
  .config/systemd/user/dms-greeter-settings-permissions.path
  .config/systemd/user/wacom-cursor-restore.service
  .local/bin/hyprland-dms-session .local/bin/wacom-cursor-restore
  .local/bin/dms-network-status .local/bin/nm-wifi-system-secret
  .local/share/wayland-sessions/hyprland-dms.desktop
)
if [[ "$machine" == laptop ]]; then
  links+=(
    .config/systemd/user/laptop-lid-awake.service
    .config/systemd/user/ssh-socks-desktop.service
    .config/systemd/user/homelab-backup-copy.service
    .config/systemd/user/homelab-backup-copy.timer
    .config/t3code-proxy/eduroam.pac
    .local/bin/t3code .local/share/applications/t3code.desktop
  )
else
  links+=(
    .xinitrc .Xresources
    .config/sunshine/wake-display.sh .config/sunshine/restore-display.sh
    .config/sunshine/apps.json
  )
fi
# Validate every source before replacing any destination.
for rel in "${links[@]}" ".config/alacritty/$machine.toml"; do
  [[ -e "$home_root/$rel" ]] || { echo "Missing source: home/$rel" >&2; exit 1; }
done

[[ -f "$repo_root/scripts/install-agent-kit.sh" && -f "$repo_root/agent/GLOBAL.md" && -d "$repo_root/agent/skills" ]] || {
  echo "Missing agent kit sources" >&2; exit 1;
}

backup_root=""
failures=0
link_file() {
  local rel="$1" src="${2:-$home_root/$1}" dst="$target_home/$1"
  if [[ -L "$dst" && "$(readlink -- "$dst")" == "$src" ]]; then
    [[ "$mode" != --check ]] || echo "OK $rel"
    return 0
  fi
  case "$mode" in
    --check) echo "MISSING or different link: $rel"; failures=$((failures + 1)); return ;;
    --dry-run) echo "LINK $dst -> $src (back up existing destination)"; return ;;
  esac
  # A parent link into home/ would write machine-local files into the shared repo.
  local parent
  parent="$(realpath -m -- "$(dirname -- "$dst")")"
  case "$parent/" in
    "$home_root/"*) echo "Destination parent points into shared home/: $dst" >&2; exit 1 ;;
  esac
  mkdir -p -- "$(dirname -- "$dst")"
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ -z "$backup_root" ]]; then
      mkdir -p -- "$target_home/.local/share/config-link-backups"
      backup_root="$(mktemp -d "$target_home/.local/share/config-link-backups/$(date +%Y%m%d-%H%M%S)-XXXXXX")"
    fi
    mkdir -p -- "$backup_root/$(dirname -- "$rel")"
    mv -- "$dst" "$backup_root/$rel"
    echo "BACKUP $dst -> $backup_root/$rel"
  fi
  ln -s -- "$src" "$dst"
  echo "LINK $dst -> $src"
}

for rel in "${links[@]}"; do link_file "$rel"; done
link_file .config/alacritty/machine.toml "$home_root/.config/alacritty/$machine.toml"

kit_args=()
[[ "$mode" == install ]] || kit_args+=("$mode")
kit_codex_root="${CODEX_HOME:-$target_home/.codex}"
kit_config_root="${XDG_CONFIG_HOME:-$target_home/.config}"
# An isolated destination must not inherit paths pointing at the real home.
if [[ -n "${CONFIG_LINK_HOME:-}" ]]; then
  kit_codex_root="$target_home/.codex"
  kit_config_root="$target_home/.config"
fi
if ! AGENT_KIT_HOME="$target_home" CODEX_HOME="$kit_codex_root" XDG_CONFIG_HOME="$kit_config_root" bash "$repo_root/scripts/install-agent-kit.sh" "${kit_args[@]}"; then
  failures=$((failures + 1))
fi
[[ -z "$backup_root" ]] || echo "Previous files: $backup_root"
if [[ "$mode" == install ]]; then
  echo "Config linked. Restart your shell; reload user units with systemctl --user daemon-reload."
fi
exit "$((failures > 0))"
