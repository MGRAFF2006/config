#!/usr/bin/env bash
# link-home.sh — Symlink config files from this repo into $HOME
# Part of ~/Documents/config
# Usage: ./scripts/link-home.sh [laptop|desktop]
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
home_root="$repo_root/home"
backup_root="$HOME/.local/share/config-link-backups/$(date +%Y%m%d-%H%M%S)"

# Detect machine type if not passed
MACHINE="${1:-}"
if [[ -z "$MACHINE" ]]; then
  hostname_val="$(hostname)"
  if [[ "$hostname_val" == *"archlinux"* ]]; then
    MACHINE="desktop"
  else
    MACHINE="laptop"
  fi
  echo "Auto-detected machine type: $MACHINE (hostname: $hostname_val)"
fi

echo "Linking config for: $MACHINE"
mkdir -p "$backup_root"

# Helper: back up and symlink
link_file() {
  local rel="$1"
  local src="$home_root/$rel"
  local dst="$HOME/$rel"

  [[ -e "$src" ]] || { echo "SKIP (no source): $src"; return; }

  mkdir -p "$(dirname -- "$dst")"

  if [[ -L "$dst" ]]; then
    rm -f "$dst"
  elif [[ -e "$dst" ]]; then
    mkdir -p "$backup_root/$(dirname -- "$rel")"
    mv "$dst" "$backup_root/$rel"
    echo "  backed up: $dst → $backup_root/$rel"
  fi

  ln -s "$src" "$dst"
  echo "  linked: $dst → $src"
}

# ── Shared links (both machines) ────────────
link_file ".zshrc"
link_file ".gitconfig"
link_file ".config/zshrc"
link_file ".config/zshrc.d"
link_file ".config/starship.toml"
link_file ".config/fastfetch"
link_file ".config/alacritty/alacritty.toml"
link_file ".config/nvim"

# ── Alacritty machine-specific override ─────
alacritty_machine_src="$home_root/.config/alacritty/${MACHINE}.toml"
alacritty_machine_dst="$HOME/.config/alacritty/machine.toml"
mkdir -p "$HOME/.config/alacritty"
if [[ -L "$alacritty_machine_dst" ]]; then
  rm -f "$alacritty_machine_dst"
elif [[ -e "$alacritty_machine_dst" ]]; then
  mv "$alacritty_machine_dst" "$backup_root/alacritty-machine.toml"
fi
ln -s "$alacritty_machine_src" "$alacritty_machine_dst"
echo "  linked: $alacritty_machine_dst → $alacritty_machine_src"

# ── Desktop-only links ───────────────────────
if [[ "$MACHINE" == "desktop" ]]; then
  link_file ".xinitrc"
  link_file ".Xresources"
fi

echo ""
echo "Done! Backup directory: $backup_root"
echo "Restart your shell or run: source ~/.zshrc"
