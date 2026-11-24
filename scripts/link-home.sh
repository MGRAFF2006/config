#!/usr/bin/env bash
# Link curated config only; package installation and service activation are separate.
# Usage: bash scripts/link-home.sh [laptop|desktop|homelab-dev] [--dry-run|--check]
set -euo pipefail

# Store a canonical path in REPLY. Command substitution alone strips trailing
# newlines, which could redirect writes to a sibling directory.
canonical_path() {
  local path
  path="$(realpath -m -- "$1" && printf .)"
  REPLY="${path%$'\n.'}"
}
canonical_path "$(dirname -- "${BASH_SOURCE[0]}")/.."; repo_root="$REPLY"
# Delegated helpers cannot represent these in the checkout path: command
# substitutions drop trailing newlines, and OpenSSH Include expands or globs
# the others, so a link could point at one checkout and SSH at another.
if [[ "$repo_root" == *[[:cntrl:]]* || "$repo_root" == *['\[]%$*?']* ]]; then
  printf 'Unsupported character in config checkout path: %q\n' "$repo_root" >&2
  exit 1
fi
canonical_path "$repo_root/home"; home_root="$REPLY"
canonical_path "${CONFIG_LINK_HOME:-$HOME}"; target_home="$REPLY"
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
  .local/bin/dms-greeter-theme-watch
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

for source in "$repo_root/systemd/user/t3code.service.d/path.conf" "$repo_root/scripts/configure-ssh.py" "$repo_root/scripts/link-plan-preflight.py" "$repo_root/ssh/workstations.conf" "$repo_root/ssh/homelab.conf"; do
  [[ -f "$source" ]] || { echo "Missing source: $source" >&2; exit 1; }
done
[[ -f "$repo_root/scripts/install-agent-kit.sh" && -f "$repo_root/agent/GLOBAL.md" && -d "$repo_root/agent/skills" ]] || {
  echo "Missing agent kit sources" >&2; exit 1;
}

backup_root=""
failures=0
ensure_local_destination() {
  canonical_path "${1%/*}/"
  case "$REPLY/" in
    "$repo_root/"*|"$home_root/"*) echo "Destination parent points into shared repo: $1" >&2; exit 1 ;;
  esac
  # Backing up a real directory moves everything inside it, including the checkout.
  if [[ -e "$1" && ! -L "$1" ]]; then
    canonical_path "$1"
    case "$repo_root/" in
      "$REPLY/"*) echo "Destination contains the config checkout: $1" >&2; exit 1 ;;
    esac
  fi
}

kit_codex_root="${CODEX_HOME:-$target_home/.codex}"
kit_config_root="${XDG_CONFIG_HOME:-$target_home/.config}"
# An isolated destination must not inherit paths pointing at the real home.
if [[ -n "${CONFIG_LINK_HOME:-}" ]]; then
  kit_codex_root="$target_home/.codex"
  kit_config_root="$target_home/.config"
fi

# Every path the apply phase changes, in order, including the SSH and agent-kit
# helpers (keep in sync with configure-ssh.py and install-agent-kit.sh).
config_backups="$target_home/.local/share/config-link-backups/new-backup"
plan=(dir "$config_backups" "")
for rel in "${links[@]}"; do plan+=(link "$target_home/$rel" "$home_root/$rel"); done
if [[ "$machine" == homelab-dev ]]; then
  plan+=(link "$target_home/.zshenv" "$repo_root/headless/zshenv")
  plan+=(link "$target_home/.config/mise/config.toml" "$repo_root/headless/mise.toml")
else
  plan+=(link "$target_home/.config/alacritty/machine.toml" "$home_root/.config/alacritty/$machine.toml")
fi
plan+=(link "$target_home/.config/systemd/user/t3code.service.d/path.conf" "$repo_root/systemd/user/t3code.service.d/path.conf")
plan+=(file "$target_home/.ssh/config" "" dir "$config_backups" "")
plan+=(dir "$target_home/.local/share/agent-kit-backups/new-backup" "")
plan+=(localize "$kit_codex_root/skills" "$repo_root/agent/skills")
plan+=(localize "$target_home/.claude/skills" "$repo_root/agent/skills")
for target in "$target_home/AGENTS.md" "$kit_codex_root/AGENTS.md" \
  "$kit_config_root/opencode/AGENTS.md" "$target_home/.claude/CLAUDE.md" \
  "$target_home/.claude/AGENTS.md"; do
  plan+=(link "$target" "$repo_root/agent/AGENTS.md")
done
plan+=(link "$target_home/.agents/skills" "$repo_root/agent/skills")
for skill in "$repo_root"/agent/skills/*; do
  [[ -f "$skill/SKILL.md" ]] || continue
  name="${skill##*/}"
  plan+=(link "$target_home/.claude/skills/$name" "$skill")
  plan+=(retire "$target_home/.cursor/skills/$name" "$skill" retire "$kit_codex_root/skills/$name" "$skill")
done
for rule in agent-kit letter personal-machines; do
  plan+=(retire "$target_home/.cursor/rules/$rule.mdc" "$repo_root/agent/AGENTS.md")
done

# Refuse shared parents, checkout ancestors and paths redirected by an earlier
# step before changing anything. Installers run the preview before packages.
if [[ "$mode" != --check ]]; then
  python3 "$repo_root/scripts/link-plan-preflight.py" "$repo_root" "$home_root" "${plan[@]}" || exit 1
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
  mkdir -p -- "${dst%/*}/"
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

if ! AGENT_KIT_HOME="$target_home" CODEX_HOME="$kit_codex_root" XDG_CONFIG_HOME="$kit_config_root" bash "$repo_root/scripts/install-agent-kit.sh" "${kit_args[@]}"; then
  failures=$((failures + 1))
fi
[[ -z "$backup_root" ]] || echo "Previous files: $backup_root"
if [[ "$mode" == install ]]; then
  echo "Config linked. Restart your shell; reload user units with systemctl --user daemon-reload."
fi
exit "$((failures > 0))"
