#!/usr/bin/env bash
# Install workstation packages from a local checkout; never update the checkout.
# Usage: bash scripts/install.sh [laptop|desktop] [--skip-aur] [--dry-run]
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
machine=""
skip_aur=false
dry_run=false
for arg in "$@"; do
  case "$arg" in
    laptop|desktop)
      [[ -z "$machine" ]] || { echo "Specify one machine" >&2; exit 2; }
      machine="$arg" ;;
    --skip-aur) skip_aur=true ;;
    --dry-run) dry_run=true ;;
    *) echo "Usage: $0 [laptop|desktop] [--skip-aur] [--dry-run]" >&2; exit 2 ;;
  esac
done
if [[ -z "$machine" ]]; then
  read -rp 'Machine [laptop/desktop]: ' machine
fi
case "$machine" in
  laptop) native_profile=laptop-kde ;;
  desktop) native_profile=desktop-dwm ;;
  *) echo "Unknown machine: $machine" >&2; exit 2 ;;
esac

read_packages() {
  awk '{sub(/#.*/, ""); if (NF) print $1}' "$@" | sort -u
}
for file in common "$native_profile" aur-common "aur-$machine"; do
  [[ -s "$repo_root/packages/$file.txt" ]] || { echo "Missing package list: $file.txt" >&2; exit 1; }
done
mapfile -t native < <(read_packages "$repo_root/packages/common.txt" "$repo_root/packages/$native_profile.txt")
mapfile -t aur < <(read_packages "$repo_root/packages/aur-common.txt" "$repo_root/packages/aur-$machine.txt")
if "$dry_run"; then
  printf 'Official packages (%s): %s\n' "${#native[@]}" "${native[*]}"
  if ! "$skip_aur"; then printf 'AUR packages (%s): %s\n' "${#aur[@]}" "${aur[*]}"; fi
  exec bash "$repo_root/scripts/link-home.sh" "$machine" --dry-run
fi

[[ "$EUID" -ne 0 ]] || { echo "Run as your normal user, with sudo available" >&2; exit 1; }
if ! grep -qx 'ID=arch' /etc/os-release; then
  echo "This installer is for Arch Linux; use setup-homelab-dev.sh on the Debian VM" >&2
  exit 1
fi
# Verify link sources before any package or service changes.
bash "$repo_root/scripts/link-home.sh" "$machine" --dry-run >/dev/null
# Arch supports complete upgrades rather than partial upgrades.
sudo pacman -Syu --needed --noconfirm "${native[@]}"
if ! "$skip_aur"; then
  if ! command -v yay >/dev/null 2>&1; then
    temporary="$(mktemp -d)"
    trap 'rm -rf -- "$temporary"' EXIT
    git clone https://aur.archlinux.org/yay-bin.git "$temporary/yay-bin"
    (cd "$temporary/yay-bin" && makepkg -si --noconfirm)
  fi
  yay -S --needed --noconfirm "${aur[@]}"
fi

bash "$repo_root/scripts/link-home.sh" "$machine"
systemctl --user daemon-reload
systemctl --user enable --now syncthing.service
for service in NetworkManager bluetooth docker libvirtd cups tailscaled; do
  sudo systemctl enable --now "$service.service"
done
if [[ "$machine" == laptop ]]; then
  sudo systemctl enable --now power-profiles-daemon.service
fi
# Preserve an already selected display manager, including greetd.
if [[ ! -e /etc/systemd/system/display-manager.service ]]; then
  sudo systemctl enable sddm.service
fi
for group in docker libvirt; do
  if ! id -nG | tr ' ' '\n' | grep -qx "$group"; then
    sudo usermod -aG "$group" "$(id -un)"
  fi
done
if [[ "$(getent passwd "$(id -un)" | cut -d: -f7)" != "$(command -v zsh)" ]]; then
  chsh -s "$(command -v zsh)"
fi
mkdir -p "$HOME/Documents" "$HOME/Projects" "$HOME/Pictures" "$HOME/Videos" "$HOME/Music"

cat <<'DONE'
Workstation packages and config installed. Log out/in for shell and group changes.

Next steps:
- Configure Syncthing at http://localhost:8384 and authenticate Tailscale.
- Sync Documents, Projects, and Documents/config; add /config to Documents/.stignore.
  Do not separately sync ~/.config/nvim or ~/.config/alacritty (symlinked config).
- Start nvim to install its plugins. Restore credentials from Bitwarden locally.
- Review firewall rules before enabling ufw. Hyprland/DMS has a separate installer.
- Desktop: restore the custom DWM checkout and its scripts before starting X.
DONE
if "$skip_aur"; then echo 'AUR installation was skipped; AUR applications still need to be installed.'; fi
