#!/usr/bin/env bash
# fix-howdy-libjxl.sh — libjxl 0.11 soname compat for python-dlib / howdy
#
# After libjxl 0.12, AUR python-dlib-git wheels may still link libjxl.so.0.11.
# Symlink to 0.12 until the package is rebuilt. Safe no-op when 0.11 exists.
#
# Needs sudo. Idempotent.
# Usage: ~/Documents/config/scripts/fix-howdy-libjxl.sh
set -euo pipefail

info() { printf '[INFO]  %s\n' "$*"; }
ok()   { printf '[OK]    %s\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then
  if [[ -z "${SUDO_ASKPASS:-}" ]] && [[ -x /usr/bin/ksshaskpass ]]; then
    export SUDO_ASKPASS=/usr/bin/ksshaskpass
  fi
  exec sudo -A -- "$0" "$@"
fi

for lib in libjxl libjxl_threads; do
  target="/usr/lib/${lib}.so.0.12"
  link="/usr/lib/${lib}.so.0.11"
  if [[ -e "$link" ]]; then
    ok "$link already present"
    continue
  fi
  if [[ ! -e "$target" ]]; then
    printf 'Missing %s — install libjxl\n' "$target" >&2
    exit 1
  fi
  ln -sf "$target" "$link"
  ok "Linked $link -> $target"
done

if python3 -c 'import dlib' 2>/dev/null; then
  ok "python-dlib import OK"
else
  printf 'dlib still fails — rebuild python-dlib-git (proxy off): yay -S --rebuild python-dlib-git\n' >&2
  exit 1
fi
