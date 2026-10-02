#!/usr/bin/env bash
# install-pam-keyring-howdy.sh — greetd/SDDM/DMS-lock PAM for Howdy + KWallet unlock
#
# Password/PIN first, Howdy fallback for login/lock; Howdy first for sudo.
# Polkit stays password-only because graphical agents do not reliably handle
# Howdy's separate PAM conversation before their password prompt.
# Also: libjxl shim, howdy-test numpy fix, DMS greeterPamExternallyManaged.
#
# Needs sudo. Idempotent.
# Usage: ~/Documents/config/scripts/install-pam-keyring-howdy.sh
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/system/pam.d"

info() { printf '[INFO]  %s\n' "$*"; }
ok()   { printf '[OK]    %s\n' "$*"; }
warn() { printf '[WARN]  %s\n' "$*"; }

for required in greetd sddm dankshell sudo polkit-1; do
  if [[ ! -f "$src/$required" ]]; then
    printf 'Missing managed PAM file: %s/%s\n' "$src" "$required" >&2
    exit 1
  fi
done

if [[ "${EUID}" -ne 0 ]]; then
  if [[ -z "${SUDO_ASKPASS:-}" ]] && [[ -x /usr/bin/ksshaskpass ]]; then
    export SUDO_ASKPASS=/usr/bin/ksshaskpass
  fi
  exec sudo -A -- "$0" "$@"
fi

stamp="$(date +%Y%m%d-%H%M%S)"
install_pam() {
  local name="$1"
  local dest="/etc/pam.d/$name"
  if [[ -f "$dest" ]]; then
    cp -a "$dest" "${dest}.backup-${stamp}"
  fi
  install -m 644 "$src/$name" "$dest"
  ok "Installed $dest"
}

if [[ ! -e /usr/lib/security/pam_howdy.so && ! -e /lib/security/pam_howdy.so ]]; then
  printf 'pam_howdy.so not found — install howdy-git first\n' >&2
  exit 1
fi

"$repo_root/scripts/fix-howdy-libjxl.sh"

# howdy test.py: sum(hist)[0] breaks on numpy 2.x (scalar). Match compare.py.
howdy_test="/usr/lib/howdy/cli/test.py"
if [[ -f "$howdy_test" ]] && grep -q 'hist_total = int(sum(hist)\[0\])' "$howdy_test"; then
  cp -a "$howdy_test" "${howdy_test}.backup-${stamp}"
  sed -i 's/hist_total = int(sum(hist)\[0\])/hist_total = int(np.sum(hist))/' "$howdy_test"
  ok "Patched howdy test.py numpy hist sum"
fi

if [[ ! -e /usr/lib/security/pam_kwallet5.so ]]; then
  printf 'pam_kwallet5.so not found — install kwallet-pam\n' >&2
  exit 1
fi

install_pam greetd
install_pam sddm
install_pam dankshell
install_pam sudo
install_pam polkit-1

# Keep distro system-auth Howdy stub disabled — sudo owns face auth explicitly.
# Re-enabling it there would prompt for a password before the camera.
if [[ -f /etc/pam.d/system-auth ]] && grep -q '^auth[[:space:]]\+sufficient[[:space:]].*pam_howdy' /etc/pam.d/system-auth; then
  warn "system-auth still has an active pam_howdy line; prefer sudo only"
fi

howdy_cfg="$repo_root/system/howdy/config.ini"
if [[ -f "$howdy_cfg" ]]; then
  install -d -m 755 /etc/howdy
  if [[ -f /etc/howdy/config.ini ]]; then
    cp -a /etc/howdy/config.ini "/etc/howdy/config.ini.backup-${stamp}"
  fi
  install -m 644 "$howdy_cfg" /etc/howdy/config.ini
  ok "Installed /etc/howdy/config.ini"
fi

# Stop DMS greeter from rewriting /etc/pam.d/greetd (would drop Howdy).
dms_settings="${SUDO_USER:+/home/$SUDO_USER}/.config/DankMaterialShell/settings.json"
if [[ -z "${SUDO_USER:-}" ]]; then
  dms_settings=""
fi
if [[ -n "$dms_settings" && -f "$dms_settings" ]]; then
  python3 - "$dms_settings" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
changed = False
for key in ("greeterPamExternallyManaged", "lockPamExternallyManaged"):
    if data.get(key) is not True:
        data[key] = True
        changed = True
if changed:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("updated", path)
else:
    print("already set", path)
PY
  ok "DMS greeter/lock PAM marked externally managed"
fi

ok "PAM stacks updated (backups: *.backup-${stamp})"
warn "Wallet unlock on typed password requires kdewallet password == login password."
warn "Face-only login cannot unlock KWallet without a sealed secret (blank wallet or howdy-tpm)."
ok "Done. Fully log out and back in for greetd/session PAM to apply."
