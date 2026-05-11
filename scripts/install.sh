#!/usr/bin/env bash
# install.sh — Reproducible Arch Linux setup for humunkulud
# Hosted at: https://github.com/MGRAFF2006/config
#
# Fresh install bootstrap:
#   curl -sL https://raw.githubusercontent.com/MGRAFF2006/config/main/scripts/install.sh | bash
#
# Or clone first and run locally:
#   git clone https://github.com/MGRAFF2006/config ~/Documents/config
#   ~/Documents/config/scripts/install.sh
#
set -euo pipefail

# ── Colors ──────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE} $*${NC}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════${NC}"; }

REPO_URL="https://github.com/MGRAFF2006/config"
REPO_DIR="$HOME/Documents/config"

# ── Detect or ask for machine type ──────────
header "humunkulud's Arch Setup"
echo ""
if [[ -n "${1:-}" ]]; then
  MACHINE="$1"
else
  echo "Which machine are you setting up?"
  echo "  1) laptop  — KDE Plasma, portable"
  echo "  2) desktop — DWM, stationary"
  echo ""
  read -rp "Enter choice [1/2] or type 'laptop'/'desktop': " choice
  case "$choice" in
    1|laptop)  MACHINE="laptop" ;;
    2|desktop) MACHINE="desktop" ;;
    *) error "Unknown choice: $choice"; exit 1 ;;
  esac
fi
success "Machine type: $MACHINE"

# ── Ensure Arch Linux ───────────────────────
if ! grep -q "^ID=arch" /etc/os-release 2>/dev/null; then
  error "This script is for Arch Linux only."
  exit 1
fi

# ── Step 1: Install yay ─────────────────────
header "Step 1: AUR Helper (yay)"
if ! command -v yay &>/dev/null; then
  info "Installing yay..."
  sudo pacman -S --needed --noconfirm git base-devel
  tmpdir="$(mktemp -d)"
  git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
  (cd "$tmpdir/yay-bin" && makepkg -si --noconfirm)
  rm -rf "$tmpdir"
  success "yay installed"
else
  success "yay already installed"
fi

# ── Step 2: Clone config repo ────────────────
header "Step 2: Config Repo"
if [[ -d "$REPO_DIR/.git" ]]; then
  info "Config repo already exists at $REPO_DIR — pulling latest..."
  git -C "$REPO_DIR" pull --ff-only || warn "Could not auto-update repo (merge conflict?)"
else
  mkdir -p "$(dirname "$REPO_DIR")"
  info "Cloning config repo to $REPO_DIR..."
  git clone "$REPO_URL" "$REPO_DIR"
  success "Config repo cloned"
fi

PKG_DIR="$REPO_DIR/packages"

# ── Step 3: Create directory structure ───────
header "Step 3: Directory Structure"
dirs=(
  "$HOME/Documents/3DPrinting"
  "$HOME/Documents/Archive"
  "$HOME/Documents/Finanzen"
  "$HOME/Documents/Gaming"
  "$HOME/Documents/JCH"
  "$HOME/Documents/Studium"
  "$HOME/Documents/config"
  "$HOME/Projects"
  "$HOME/Pictures"
  "$HOME/Videos"
  "$HOME/Music"
)
for d in "${dirs[@]}"; do
  mkdir -p "$d"
  info "  ensured: $d"
done
success "Directory structure ready"

# ── Step 4: Install common packages ──────────
header "Step 4: Common Packages (pacman)"
info "Installing common packages..."
grep -v '^#' "$PKG_DIR/common.txt" | grep -v '^$' | \
  sudo pacman -S --needed --noconfirm - || warn "Some packages may have failed (check above)"
success "Common packages done"

# ── Step 5: Machine-specific packages ────────
header "Step 5: Machine-Specific Packages (pacman)"
pkg_file="$PKG_DIR/${MACHINE}-dwm.txt"
[[ "$MACHINE" == "laptop" ]] && pkg_file="$PKG_DIR/laptop-kde.txt"

if [[ -f "$pkg_file" ]]; then
  info "Installing packages from $pkg_file..."
  grep -v '^#' "$pkg_file" | grep -v '^$' | \
    sudo pacman -S --needed --noconfirm - || warn "Some machine-specific packages may have failed"
  success "Machine-specific packages done"
else
  warn "No machine-specific package file found: $pkg_file"
fi

# ── Step 6: AUR common packages ──────────────
header "Step 6: AUR Common Packages"
info "Installing common AUR packages..."
grep -v '^#' "$PKG_DIR/aur-common.txt" | grep -v '^$' | \
  xargs -r yay -S --needed --noconfirm || warn "Some AUR packages may have failed"
success "AUR common packages done"

# ── Step 7: AUR machine-specific packages ────
header "Step 7: AUR Machine-Specific Packages"
aur_file="$PKG_DIR/aur-${MACHINE}.txt"
if [[ -f "$aur_file" ]] && grep -qv '^#' "$aur_file" 2>/dev/null; then
  info "Installing machine-specific AUR packages from $aur_file..."
  grep -v '^#' "$aur_file" | grep -v '^$' | \
    xargs -r yay -S --needed --noconfirm || warn "Some machine-specific AUR packages may have failed"
  success "Machine-specific AUR packages done"
else
  info "No machine-specific AUR packages for $MACHINE"
fi

# ── Step 8: Symlink config files ─────────────
header "Step 8: Symlink Config Files"
info "Running link-home.sh for $MACHINE..."
bash "$REPO_DIR/scripts/link-home.sh" "$MACHINE"
success "Config files linked"

# ── Step 9: Set default shell to ZSH ─────────
header "Step 9: Default Shell"
if [[ "$SHELL" != "$(which zsh)" ]]; then
  info "Changing default shell to zsh..."
  chsh -s "$(which zsh)"
  success "Default shell set to zsh (takes effect on next login)"
else
  success "ZSH already default shell"
fi

# ── Step 10: Minimal bash fallback ───────────
header "Step 10: Bash Fallback"
BASHRC="$HOME/.bashrc"
BASHRC_CONTENT='# ~/.bashrc — minimal fallback, real config is in ZSH
[[ $- != *i* ]] && return
# Launch zsh if available and not already in zsh
if command -v zsh &>/dev/null && [[ -z "${ZSH_VERSION}" ]]; then
  exec zsh
fi'

if [[ -L "$BASHRC" ]]; then
  info "Removing old .bashrc symlink (mybash)..."
  rm -f "$BASHRC"
  echo "$BASHRC_CONTENT" > "$BASHRC"
  success "Minimal .bashrc written"
elif [[ -f "$BASHRC" ]]; then
  if grep -q "mybash\|zachbrowne\|fastfetch" "$BASHRC" 2>/dev/null; then
    info "Replacing old bashrc with minimal version (backup at ~/.bashrc.bak)..."
    cp "$BASHRC" "$HOME/.bashrc.bak"
    echo "$BASHRC_CONTENT" > "$BASHRC"
    success "Minimal .bashrc written (backup at ~/.bashrc.bak)"
  else
    info ".bashrc exists and looks custom — leaving it alone"
  fi
fi

# ── Step 11: Enable systemd services ─────────
header "Step 11: Systemd Services"

enable_user_service() {
  local svc="$1"
  if systemctl --user list-unit-files "$svc" &>/dev/null; then
    systemctl --user enable --now "$svc" 2>/dev/null && success "  enabled: $svc" || warn "  failed: $svc"
  else
    warn "  not found: $svc"
  fi
}

enable_system_service() {
  local svc="$1"
  if systemctl list-unit-files "$svc" &>/dev/null; then
    sudo systemctl enable --now "$svc" 2>/dev/null && success "  enabled: $svc" || warn "  failed: $svc"
  else
    warn "  not found: $svc"
  fi
}

info "Enabling common user services..."
enable_user_service "syncthing.service"

info "Enabling common system services..."
enable_system_service "NetworkManager.service"
enable_system_service "bluetooth.service"
enable_system_service "docker.service"
enable_system_service "libvirtd.service"
enable_system_service "cups.service"
enable_system_service "ufw.service"

# Docker group
if ! groups | grep -q docker; then
  sudo usermod -aG docker "$USER"
  info "Added $USER to docker group (log out to take effect)"
fi

# libvirt group
if ! groups | grep -q libvirt; then
  sudo usermod -aG libvirt "$USER"
  info "Added $USER to libvirt group (log out to take effect)"
fi

if [[ "$MACHINE" == "laptop" ]]; then
  info "Enabling laptop services..."
  enable_system_service "sddm.service"
  enable_system_service "power-profiles-daemon.service"
fi

if [[ "$MACHINE" == "desktop" ]]; then
  info "Enabling desktop services..."
  enable_system_service "sddm.service"
fi

# ── Step 12: Neovim setup ────────────────────
header "Step 12: Neovim"
if [[ -d "$HOME/.config/nvim" ]]; then
  info "Neovim config linked. Run 'nvim' to trigger lazy.nvim plugin install."
  success "Neovim config ready"
else
  warn "No nvim config found — link-home.sh may not have linked it"
fi

# ── Done! ────────────────────────────────────
header "Setup Complete!"
echo ""
echo -e "${GREEN}${BOLD}Your $MACHINE is ready!${NC}"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo -e "  1. Log out and back in (or reboot) for shell + group changes to take effect"
echo -e "  2. Configure Syncthing: ${YELLOW}http://localhost:8384${NC}"
echo -e "     → Add the other machine's device ID to start bidirectional sync"
echo -e "  3. Sync folders to configure:"
echo -e "     ~/Documents/  ~/Projects/  ~/Documents/config/"
echo -e "     ~/.config/nvim/  ~/.config/alacritty/"
echo -e "  4. Run 'nvim' to trigger plugin installation"
if [[ "$MACHINE" == "desktop" ]]; then
  echo -e "  5. Install MesloLGS or JetBrainsMono Nerd Font if not already present"
  echo -e "     https://www.nerdfonts.com/font-downloads"
  echo -e "  6. Build/install DWM: ~/dwm/  (or from suckless.org)"
fi
echo ""
