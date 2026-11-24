#!/usr/bin/env bash
# install-pam-keyring-howdy.sh — greetd/SDDM/DMS-lock PAM for Howdy + KWallet unlock
#
# Password/PIN first, Howdy fallback for greetd, SDDM and the DMS lock; Howdy
# first for sudo. The DMS lock patch starts the fallback on wake.
# Polkit stays password-only because graphical agents do not reliably handle
# Howdy's separate PAM conversation before their password prompt.
# Also: howdy-test numpy fix, DMS greeterPamExternallyManaged.
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

# Refuse before changing anything when the DMS settings cannot be switched to
# the managed lock stack safely (e.g. DMS requires a security key as a second
# factor, which an externally managed lock would skip). 3 = no settings yet.
check_dms_settings() {
  local status=0
  python3 "$repo_root/scripts/configure-dms-lock-pam.py" --check "$1" || status=$?
  if [[ "$status" -ne 0 && "$status" -ne 3 ]]; then
    printf 'DMS settings check failed (see above); no PAM or Howdy file was changed\n' >&2
    exit 1
  fi
}

if [[ "${EUID}" -ne 0 ]]; then
  # sudo drops XDG_CONFIG_HOME, and DMS_POLICY_LOCK_SETTINGS, which a shell not
  # started by `dms run` inherits: check with the caller's environment first.
  check_dms_settings "${XDG_CONFIG_HOME:-$HOME/.config}"
  exec sudo bash "$0" "${XDG_CONFIG_HOME:-$HOME/.config}"
fi
dms_config_home="${1:-}"
if [[ -z "$dms_config_home" && -n "${SUDO_USER:-}" ]]; then
  dms_config_home="$(getent passwd "$SUDO_USER" | cut -d: -f6)/.config"
fi
if [[ -n "$dms_config_home" ]]; then
  check_dms_settings "$dms_config_home"
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

if ! python3 -c 'import dlib'; then
  printf 'python-dlib cannot load; rebuild it against the current libraries before changing PAM\n' >&2
  exit 1
fi

if [[ ! -e /usr/lib/security/pam_kwallet5.so ]]; then
  printf 'pam_kwallet5.so not found — install kwallet-pam\n' >&2
  exit 1
fi

# Stop DMS from rewriting the greeter PAM (would drop Howdy) and select the
# managed lock stack in the settings file DMS 2.1 reads. This runs before any
# PAM or Howdy file changes, so a failed settings write leaves them all as they
# were (the editor replaces the settings file atomically). A later failure
# leaves the settings pointing at /etc/pam.d/dankshell with whatever content it
# had; PAM files are not rolled back, and the .backup-* copies stay.
if [[ -z "$dms_config_home" ]]; then
  warn "Unknown invoking user; run configure-dms-lock-pam.py ~/.config as that user"
else
  dms_status=0
  python3 "$repo_root/scripts/configure-dms-lock-pam.py" "$dms_config_home" || dms_status=$?
  if [[ "$dms_status" -eq 3 ]]; then
    warn "DMS greeter/lock PAM settings not updated"
  elif [[ "$dms_status" -ne 0 ]]; then
    printf 'DMS settings were not updated (see above); no PAM or Howdy file was changed\n' >&2
    exit 1
  fi
fi

# howdy test.py: sum(hist)[0] breaks on numpy 2.x (scalar). Match compare.py.
howdy_test="/usr/lib/howdy/cli/test.py"
if [[ -f "$howdy_test" ]] && grep -q 'hist_total = int(sum(hist)\[0\])' "$howdy_test"; then
  cp -a "$howdy_test" "${howdy_test}.backup-${stamp}"
  sed -i 's/hist_total = int(sum(hist)\[0\])/hist_total = int(np.sum(hist))/' "$howdy_test"
  ok "Patched howdy test.py numpy hist sum"
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

ok "PAM stacks updated (backups: *.backup-${stamp})"
warn "Wallet unlock on typed password requires kdewallet password == login password."
warn "Face-only KWallet unlock requires separate TPM enrollment via install-howdy-kwallet-tpm.py."
ok "Done. Fully log out and back in for greetd/session PAM to apply."
