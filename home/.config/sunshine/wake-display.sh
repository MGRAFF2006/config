#!/bin/sh
# Sunshine prep "do": wake displays and keep them awake during the stream.
#
# Sunshine runs as a systemd --user service without the graphical session's
# XAUTHORITY, so we rebuild a short-lived auth file from the running Xorg
# cookie (xinit often stores it under /tmp/serverauth.*).
#
# Blocks for a couple of seconds after wake so panels finish link training
# before Sunshine starts capturing — important when monitors were in DPMS off.
set -eu

LOG="${XDG_CACHE_HOME:-$HOME/.cache}/sunshine-wake.log"
mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

export DISPLAY="${DISPLAY:-:0}"

log "wake-display: start DISPLAY=$DISPLAY"

# Find Xorg (binary may be /usr/lib/Xorg; process name is still Xorg)
xorg_pid="$(pgrep -n -x Xorg 2>/dev/null || true)"
if [ -z "$xorg_pid" ]; then
  xorg_pid="$(pgrep -n -f '/Xorg( |$)|/usr/lib/Xorg' 2>/dev/null || true)"
fi
if [ -z "$xorg_pid" ]; then
  log "wake-display: no Xorg process found"
  echo "wake-display: no Xorg process found" >&2
  # Still exit 0 so Sunshine can attempt KMS capture; nothing more we can do.
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
  log "wake-display: cannot find X server auth file"
  echo "wake-display: cannot find X server auth file" >&2
  exit 0
fi

cookie="$(xauth -f "$server_auth" list 2>/dev/null | awk '/unix:0/{print $NF; exit}')"
if [ -z "$cookie" ]; then
  cookie="$(xauth -f "$server_auth" list 2>/dev/null | awk '{print $NF; exit}')"
fi
if [ -z "$cookie" ]; then
  log "wake-display: no MIT-MAGIC-COOKIE in $server_auth"
  echo "wake-display: no MIT-MAGIC-COOKIE in $server_auth" >&2
  exit 0
fi

auth="$(mktemp)"
trap 'rm -f "$auth"' EXIT INT TERM
host="$(hostname)"
xauth -f "$auth" add :0 MIT-MAGIC-COOKIE-1 "$cookie"
xauth -f "$auth" add "${host}/unix:0" MIT-MAGIC-COOKIE-1 "$cookie"
# xinit may have written the cookie under the install-time hostname
xauth -f "$auth" add archlinux/unix:0 MIT-MAGIC-COOKIE-1 "$cookie" 2>/dev/null || true

export XAUTHORITY="$auth"

# 1) Force DPMS on, disable blanking for the stream duration
xset dpms force on 2>/dev/null || log "wake-display: xset dpms force on failed"
xset s reset 2>/dev/null || true
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true

# 2) Re-assert connected outputs (helps some panels that ignore DPMS alone)
if command -v xrandr >/dev/null 2>&1; then
  xrandr --query 2>/dev/null | awk '/ connected/{print $1}' | while read -r out; do
    [ -n "$out" ] || continue
    xrandr --output "$out" --auto 2>/dev/null || true
  done
  # Prefer saved dwm layout if present
  if [ -x "$HOME/dwm/scripts/display_apply.sh" ]; then
    "$HOME/dwm/scripts/display_apply.sh" 2>/dev/null || true
  fi
fi

# 3) Nudge input so idle/DPMS watchers see activity
if command -v xdotool >/dev/null 2>&1; then
  xdotool key Shift_L 2>/dev/null || true
elif command -v ydotool >/dev/null 2>&1; then
  ydotool key 42:1 42:0 2>/dev/null || true
fi

# 4) Give monitors time to wake before Sunshine grabs frames
sleep 2

# Confirm DPMS is still forced on after the wait
xset dpms force on 2>/dev/null || true

log "wake-display: done (xorg_pid=$xorg_pid auth=$server_auth)"
exit 0
