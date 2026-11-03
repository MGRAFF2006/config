#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mode=${1:---check}
if [[ $# -gt 1 || ! $mode =~ ^--(check|install|plan)$ ]]; then
  echo "Usage: $0 [--check|--plan|--install]" >&2
  exit 2
fi

# shellcheck source=/dev/null
source /etc/os-release
case "$ID" in
  arch) package_list="$repo/packages/asahi-build-arch.txt" ;;
  debian)
    [[ $VERSION_ID == 13 ]] || { echo "This package list targets Debian 13." >&2; exit 1; }
    package_list="$repo/packages/asahi-build-debian.txt"
    ;;
  *) echo "Supported hosts: Arch Linux and Debian 13." >&2; exit 1 ;;
esac
mapfile -t packages < <(awk '{sub(/#.*/, ""); if (NF) print $1}' "$package_list")

case "$mode" in
  --plan) printf '%s\n' "${packages[@]}" ;;
  --install)
    if [[ $ID == arch ]]; then
      # Do not refresh databases separately: Arch does not support partial upgrades.
      sudo pacman -S --needed --noconfirm "${packages[@]}"
    else
      sudo apt-get update
      sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
    fi
    bash "$0" --check
    ;;
  --check)
    missing=()
    for package in "${packages[@]}"; do
      if [[ $ID == arch ]]; then
        pacman -Q "$package" >/dev/null 2>&1 || missing+=("$package")
      else
        status=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)
        [[ $status == installed ]] || missing+=("$package")
      fi
    done
    if ((${#missing[@]})); then
      printf 'Missing packages: %s\n' "${missing[*]}" >&2
      echo "Install with: bash $0 --install" >&2
      exit 1
    fi
    echo "Asahi build packages are installed. Run scripts/asahi-build.sh doctor SOURCE to check the kernel toolchain."
    ;;
esac
