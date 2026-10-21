#!/bin/sh
# Sunshine prep "undo": restore normal power management after the stream.
set -eu

LOG="${XDG_CACHE_HOME:-$HOME/.cache}/sunshine-wake.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

export DISPLAY="${DISPLAY:-:0}"
log "restore-display: start"

xorg_pid="$(pgrep -n -x Xorg 2>/dev/null || true)"
if [ -z "$xorg_pid" ]; then
  xorg_pid="$(pgrep -n -f '/Xorg( |$)|/usr/lib/Xorg' 2>/dev/null || true)"
fi
if [ -z "$xorg_pid" ]; then
  log "restore-display: no Xorg process found"
  exit 0
fi

server_auth="$(tr '\0' ' ' < "/proc/$xorg_pid/cmdline" | sed -n 's/.*-auth \([^ ]*\).*/\1/p')"
if [ -z "${server_auth:-}" ] || [ ! -r "$server_auth" ]; then
  server_auth="$(ls -t /tmp/serverauth.* 2>/dev/null | head -n1 || true)"
fi
if [ -z "${server_auth:-}" ] || [ ! -r "$server_auth" ]; then
  if [ -r "$HOME/.Xauthority" ]; then
    server_auth="$HOME/.Xauthority"
  fi
fi
if [ -z "${server_auth:-}" ] || [ ! -r "$server_auth" ]; then
  log "restore-display: cannot find X server auth file"
  exit 0
fi

cookie="$(xauth -f "$server_auth" list 2>/dev/null | awk '/unix:0/{print $NF; exit}')"
if [ -z "$cookie" ]; then
  cookie="$(xauth -f "$server_auth" list 2>/dev/null | awk '{print $NF; exit}')"
fi
if [ -z "$cookie" ]; then
  log "restore-display: no MIT-MAGIC-COOKIE in $server_auth"
  exit 0
fi

auth="$(mktemp)"
trap 'rm -f "$auth"' EXIT INT TERM
host="$(hostname)"
xauth -f "$auth" add :0 MIT-MAGIC-COOKIE-1 "$cookie"
xauth -f "$auth" add "${host}/unix:0" MIT-MAGIC-COOKIE-1 "$cookie"
xauth -f "$auth" add archlinux/unix:0 MIT-MAGIC-COOKIE-1 "$cookie" 2>/dev/null || true

export XAUTHORITY="$auth"

# Re-enable DPMS / screensaver blanking for normal idle behaviour
xset +dpms 2>/dev/null || true
xset s on 2>/dev/null || true
# Standby/suspend/off timeouts (seconds). Off after 10 minutes idle.
xset dpms 600 600 600 2>/dev/null || true

log "restore-display: done"
exit 0
