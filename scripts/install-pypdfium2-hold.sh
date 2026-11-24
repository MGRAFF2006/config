#!/usr/bin/env bash
# Persist the single-package workaround without replacing pacman's configuration.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$repo_root/system/pacman/pypdfium2-hold.conf"
# PYPDFIUM2_HOLD_ROOT is for fixture tests only; normal use leaves it unset.
root="${PYPDFIUM2_HOLD_ROOT:-}"
pacman_conf="$root/etc/pacman.conf"
destination="$root/etc/pacman.d/pypdfium2-hold.conf"
include="Include = $destination"
mode="${1:-install}"
case "$mode" in install|--dry-run|--check) ;; *) echo "Usage: $0 [--dry-run|--check]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || { echo 'Expected at most one argument' >&2; exit 2; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# Print the section of every line that includes the managed file, using
# pacman's rules: '#' starts a comment and surrounding whitespace is ignored.
include_sections() {
  awk -v target="$destination" '
    { line = $0; sub(/#.*/, "", line); gsub(/^[ \t]+|[ \t]+$/, "", line) }
    line ~ /^\[.*\]$/ { section = substr(line, 2, length(line) - 2); next }
    line ~ /^Include[ \t]*=/ {
      value = line; sub(/^Include[ \t]*=[ \t]*/, "", value)
      if (value == target) print (section == "" ? "(none)" : section)
    }
  ' "$pacman_conf"
}

# The hold only applies when its Include sits in [options]; elsewhere pacman
# ignores IgnorePkg with a warning, so a misplaced line must not pass or block.
check_include_placement() {
  local misplaced
  misplaced="$(include_sections | grep -vx options | sort -u | paste -sd ' ' || true)"
  [[ -z "$misplaced" ]] || fail "$pacman_conf includes $destination outside [options] (in: $misplaced). Move it under [options] with sudoedit."
}
included_in_options() { grep -Fxq options <<<"$(include_sections)"; }

if [[ "$mode" == --dry-run ]]; then
  echo "Install $destination and add its Include under [options] in $pacman_conf."
  echo 'Hold only python-pypdfium2; preserve all other settings and install no packages.'
  exit
fi
if [[ "$mode" == --check ]]; then
  cmp -s -- "$source_file" "$destination" || fail "$destination is missing or differs from $source_file."
  check_include_placement
  included_in_options || fail "$pacman_conf does not include $destination under [options]."
  pacman-conf --config "$pacman_conf" IgnorePkg | tr ' ' '\n' | grep -Fxq python-pypdfium2 \
    || fail 'pacman-conf does not report python-pypdfium2 in IgnorePkg.'
  echo 'PASS: pacman and yay persistently hold python-pypdfium2.'
  exit
fi
[[ -n "$root" || $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

# Refuse unexpected layouts before writing anything. Editing in place would
# replace a symlink with a regular file and disconnect its managed target.
[[ ! -L "$pacman_conf" ]] || fail "$pacman_conf is a symlink; add '$include' under [options] in its target manually."
[[ ! -L "$destination" ]] || fail "$destination is a symlink; refusing to replace it."
[[ -f "$pacman_conf" ]] || fail "$pacman_conf is not a regular file."
# Exactly one [options] header, so the Include cannot land inside a repository.
[[ "$(grep -Fxc '[options]' "$pacman_conf")" == 1 ]] || fail "$pacman_conf needs exactly one exact '[options]' line."
check_include_placement

mkdir -p "$root/var/backups/config-pypdfium2-hold"
backup="$(mktemp -d "$root/var/backups/config-pypdfium2-hold/$(date +%Y-%m-%d)-XXXXXXXX")"
cp -a -- "$pacman_conf" "$backup/pacman.conf"
if [[ -e "$destination" ]]; then
  cp -a -- "$destination" "$backup/pypdfium2-hold.conf"
fi
install -D -m 644 -- "$source_file" "$destination"
if ! included_in_options; then
  sed -i "\\|^\\[options\\]\$|a $include" "$pacman_conf"
fi
echo "Previous configuration: $backup"
bash "$0" --check
