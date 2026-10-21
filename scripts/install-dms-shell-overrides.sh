#!/usr/bin/env bash
# install-dms-shell-overrides.sh — Apply local DMS shell overrides and patches
# DMS 1.5.x always runs qs from /usr/share/quickshell/dms. Re-run after
# `dms-shell` package updates.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
system_shell="/usr/share/quickshell/dms"
overrides="${repo_root}/home/.config/DankMaterialShell/shell-overrides"
patches="${repo_root}/home/.config/DankMaterialShell/shell-patches"
backup_root="${HOME}/.local/share/dms-shell-backups"
pkg_stamp="$(pacman -Q dms-shell 2>/dev/null | awk '{print $1"-"$2}' || echo unknown)"

if [[ ! -d "$system_shell" ]]; then
  echo "SKIP: $system_shell not found (install dms-shell first)" >&2
  exit 0
fi

files=()
if [[ -d "$overrides" ]]; then
  mapfile -t files < <(cd "$overrides" && find . -type f ! -path './.*' | sed 's|^\./||')
fi

echo "Patching dms-shell ($pkg_stamp) with ${#files[@]} file(s)..."

for rel in "${files[@]}"; do
  src="${overrides}/${rel}"
  dest="${system_shell}/${rel}"
  if [[ ! -f "$dest" ]]; then
    sudo mkdir -p "$(dirname -- "$dest")"
    sudo cp -- "$src" "$dest"
    echo "  added:    $rel"
    continue
  fi
  backup_dir="${backup_root}/${pkg_stamp}/$(dirname -- "$rel")"
  mkdir -p "$backup_dir"
  if [[ ! -f "${backup_dir}/${rel##*/}" ]]; then
    sudo cp -- "$dest" "${backup_dir}/${rel##*/}"
    echo "  backed up: $rel"
  fi
  sudo cp -- "$src" "$dest"
  echo "  patched:  $rel"
done

if [[ -d "$patches" ]]; then
  mapfile -t patch_files < <(find "$patches" -maxdepth 1 -type f -name '*.patch' -printf '%f\n' | sort)
  for patch_name in "${patch_files[@]}"; do
    patch_file="${patches}/${patch_name}"
    if sudo patch --dry-run --forward --batch -p1 -d "$system_shell" --input="$patch_file" >/dev/null 2>&1; then
      sudo patch --forward --batch -p1 -d "$system_shell" --input="$patch_file"
      echo "  patched:  $patch_name"
    elif sudo patch --dry-run --reverse --batch -p1 -d "$system_shell" --input="$patch_file" >/dev/null 2>&1; then
      echo "  current:  $patch_name"
    else
      echo "ERROR: patch does not apply cleanly: $patch_name" >&2
      exit 1
    fi
  done
fi

echo "Done. Restart DMS: dms restart"
