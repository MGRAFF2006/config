#!/usr/bin/env bash
# Install the single-package hold as a pacman drop-in. Adding its Include to
# pacman.conf stays a one-line manual edit; this script never edits pacman.conf.
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
# No grep -q: exiting early could SIGPIPE tr and fail the pipeline.
holds() { tr ' ' '\n' | grep -Fx python-pypdfium2 >/dev/null; }

if [[ "$mode" == --check ]]; then
  # Read-only: pacman itself decides what the configuration means.
  # Test the type first: cmp would block on a FIFO.
  [[ -f "$destination" && ! -L "$destination" ]] || fail "$destination is missing or not a regular file."
  cmp -s -- "$source_file" "$destination" || fail "$destination differs from $source_file."
  command -v pacman-conf >/dev/null || fail 'pacman-conf is not installed.'
  errors="$(mktemp)"; without="$(mktemp)"
  trap 'rm -f -- "$errors" "$without"' EXIT
  ignored="$(pacman-conf --config "$pacman_conf" IgnorePkg 2>"$errors")" \
    || fail "pacman-conf cannot parse $pacman_conf: $(cat -- "$errors")"
  # Pacman warns about IgnorePkg read outside [options], e.g. a misplaced
  # Include or a repository glob that matches the drop-in. Match the file name:
  # the path in the warning is spelled the way the Include spelled it.
  ! grep -Fq -- "${destination##*/}" "$errors" || fail "pacman warns about the drop-in: $(cat -- "$errors")"
  holds <<<"$ignored" || fail "pacman-conf does not report python-pypdfium2 in IgnorePkg; add '$include' under [options]."
  # The drop-in's own entry must be in effect: without the Include line(s)
  # for it, its literal IgnorePkg entry must disappear. (A separate pattern
  # such as python-pypdfium? may hold the package too; that is still a hold.)
  awk -v target="$destination" '
    { line = $0; gsub(/^[ \t\r]+|[ \t\r]+$/, "", line) }
    line ~ /^Include[ \t]*=/ { value = line; sub(/^Include[ \t]*=[ \t]*/, "", value); if (value == target) next }
    { print }
  ' "$pacman_conf" >"$without"
  ignored="$(pacman-conf --config "$without" IgnorePkg 2>/dev/null)" \
    || fail "pacman-conf cannot parse $pacman_conf without '$include'."
  if holds <<<"$ignored"; then
    fail "IgnorePkg still lists python-pypdfium2 without '$include'; another IgnorePkg line or a glob Include provides it."
  fi
  echo 'PASS: the drop-in is included under [options] and pacman holds python-pypdfium2.'
  exit
fi

# Refuse anything but a regular file before writing. A directory would
# receive a nested copy; a symlink would redirect the write elsewhere.
if [[ -L "$destination" || ( -e "$destination" && ! -f "$destination" ) ]]; then
  fail "$destination exists but is not a regular file; remove or move it by hand."
fi
if [[ "$mode" == --dry-run ]]; then
  echo "Install $source_file as $destination, backing up a differing existing file."
  echo "Leave $pacman_conf unchanged and print the Include line to add under [options] by hand."
  exit
fi
[[ -n "$root" || $EUID -eq 0 ]] || exec sudo bash "$0" "$@"

if [[ -f "$destination" ]] && ! cmp -s -- "$source_file" "$destination"; then
  mkdir -p "$root/var/backups/config-pypdfium2-hold"
  backup="$(mktemp -d "$root/var/backups/config-pypdfium2-hold/$(date +%Y-%m-%d)-XXXXXXXX")"
  cp -a -- "$destination" "$backup/pypdfium2-hold.conf"
  echo "Previous drop-in: $backup/pypdfium2-hold.conf"
fi
install -D -m 644 -- "$source_file" "$destination"
echo "Installed $destination."

if bash "$0" --check >/dev/null 2>&1; then
  echo 'PASS: pacman already includes the drop-in under [options].'
else
  editable="$(readlink -f -- "$pacman_conf")"
  echo "To activate the hold, add this line directly below [options] in $editable:"
  echo "  $include"
  echo "Use: sudoedit $editable"
  echo "Then verify: bash $0 --check"
fi
