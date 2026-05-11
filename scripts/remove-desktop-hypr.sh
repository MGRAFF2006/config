#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
manifest="$repo_root/packages/remove-desktop.txt"

mapfile -t packages < <(pacman -Qq | rg -x -f "$manifest" || true)

if [ "${#packages[@]}" -eq 0 ]; then
  printf 'No matching packages installed.\n'
  exit 0
fi

printf 'Removing packages:\n'
printf '  %s\n' "${packages[@]}"
sudo pacman -Rns "${packages[@]}"
