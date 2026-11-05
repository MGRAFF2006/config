#!/usr/bin/env bash
# Link curated config only; package installation and service activation are separate.
# Usage: bash scripts/link-home.sh [laptop|desktop|homelab-dev] [--dry-run|--check]
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
home_root="$(realpath -m -- "$repo_root/home")"
target_home="$(realpath -m -- "${CONFIG_LINK_HOME:-$HOME}")"
mode=install
machine=""
for arg in "$@"; do
  case "$arg" in
    laptop|desktop|homelab-dev)
      [[ -z "$machine" ]] || { echo "Specify one machine" >&2; exit 2; }
      machine="$arg" ;;
    --dry-run|--check)
      [[ "$mode" == install ]] || { echo "Specify one mode" >&2; exit 2; }
      mode="$arg" ;;
    *) echo "Usage: $0 [laptop|desktop|homelab-dev] [--dry-run|--check]" >&2; exit 2 ;;
  esac
done
if [[ -z "$machine" ]]; then
  machine="${MACHINE_TYPE:-}"
  if [[ -z "$machine" ]] && command -v tailscale >/dev/null 2>&1; then
    machine="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["HostName"])' 2>/dev/null || true)"
  fi
fi
case "$machine" in
  laptop|desktop|homelab-dev) ;;
  *) echo "Pass laptop|desktop|homelab-dev explicitly; Tailscale identity is unavailable or unsupported" >&2; exit 2 ;;
esac

if [[ "$machine" == homelab-dev ]]; then
  links=(.zshrc .bashrc .config/zshrc .config/starship.toml .config/nvim
         .config/zshrc.d/homelab-dev.zsh)
else
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
fi
# Validate every source before replacing any destination.
if [[ "$machine" == homelab-dev ]]; then
  for source in "$repo_root/headless/zshenv" "$repo_root/headless/mise.toml"; do
    [[ -f "$source" ]] || { echo "Missing source: $source" >&2; exit 1; }
  done
else
  [[ -f "$home_root/.config/alacritty/$machine.toml" ]] || { echo "Missing terminal profile" >&2; exit 1; }
fi
for rel in "${links[@]}"; do
  [[ -e "$home_root/$rel" ]] || { echo "Missing source: home/$rel" >&2; exit 1; }
done

for source in "$repo_root/systemd/user/t3code.service.d/path.conf" "$repo_root/scripts/configure-ssh.py" "$repo_root/ssh/workstations.conf" "$repo_root/ssh/homelab.conf"; do
  [[ -f "$source" ]] || { echo "Missing source: $source" >&2; exit 1; }
done
[[ -f "$repo_root/scripts/install-agent-kit.sh" && -f "$repo_root/agent/GLOBAL.md" && -d "$repo_root/agent/skills" ]] || {
  echo "Missing agent kit sources" >&2; exit 1;
}

backup_root=""
failures=0
ensure_local_destination() {
  local parent
  parent="$(realpath -m -- "$(dirname -- "$1")")"
  case "$parent/" in
    "$repo_root/"*|"$home_root/"*) echo "Destination parent points into shared repo: $1" >&2; exit 1 ;;
  esac
}

# Reject shared parents and backup aliases before changing any existing links.
if [[ "$mode" == install ]]; then
  for rel in "${links[@]}"; do ensure_local_destination "$target_home/$rel"; done
  if [[ "$machine" == homelab-dev ]]; then
    ensure_local_destination "$target_home/.zshenv"
    ensure_local_destination "$target_home/.config/mise/config.toml"
  else
    ensure_local_destination "$target_home/.config/alacritty/machine.toml"
  fi
  ensure_local_destination "$target_home/.config/systemd/user/t3code.service.d/path.conf"
  ensure_local_destination "$target_home/.ssh/config"
  ensure_local_destination "$target_home/.local/share/config-link-backups/new-backup"
fi

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
  ensure_local_destination "$dst"
  mkdir -p -- "$(dirname -- "$dst")"
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ -z "$backup_root" ]]; then
      ensure_local_destination "$target_home/.local/share/config-link-backups/new-backup"
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
if [[ "$machine" == homelab-dev ]]; then
  link_file .zshenv "$repo_root/headless/zshenv"
  link_file .config/mise/config.toml "$repo_root/headless/mise.toml"
else
  link_file .config/alacritty/machine.toml "$home_root/.config/alacritty/$machine.toml"
fi

kit_args=()
[[ "$mode" == install ]] || kit_args+=("$mode")
link_file .config/systemd/user/t3code.service.d/path.conf "$repo_root/systemd/user/t3code.service.d/path.conf"
if ! CONFIG_LINK_HOME="$target_home" python3 "$repo_root/scripts/configure-ssh.py" "$machine" "${kit_args[@]}"; then
  failures=$((failures + 1))
fi

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
