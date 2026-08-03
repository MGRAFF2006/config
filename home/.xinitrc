#!/bin/sh
# ~/.xinitrc — Desktop (DWM) X11 startup
# Managed by ~/Documents/config

# Ensure /usr/local/bin (dwm) and ~/.local/bin (qs-launcher/qs-powermenu) are in PATH
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# Set cursor theme
xsetroot -cursor_name left_ptr &

# Load X resources
[ -f ~/.Xresources ] && xrdb -merge ~/.Xresources

# Multi-monitor layout is handled by ~/dwm/scripts/display_apply.sh (run from
# dwm autostart), which applies the saved profile in ~/.config/dwm/display.conf
# or falls back to enabling all connected outputs. Don't hardcode outputs here —
# the output names change (e.g. DisplayPort-0 -> DisplayPort-2), which is what
# previously broke the layout.

# Start notification daemon
dunst &

# Start compositor (picom for transparency/blur)
picom --config "$HOME/.config/picom.conf" --daemon 2>/dev/null &

# Wallpaper is set from dwm autostart via ~/dwm/scripts/wallpaper.sh, which
# paints ONE image per monitor (feh --bg-fill img img ...) so both screens are
# covered and nothing spills/tiles. (Kept out of here to avoid a stale
# single-image feh call clobbering it.)

# Idle -> auto-lock manager (xss-lock + xidlehook). Locks after 5 min idle
# and on suspend. See ~/dwm/scripts/idle.sh
[ -x "$HOME/dwm/scripts/idle.sh" ] && "$HOME/dwm/scripts/idle.sh" &

# Start DWM — prefer locally built, fall back to /usr/local
if [ -x "$HOME/dwm/dwm" ]; then
  exec "$HOME/dwm/dwm" >"$HOME/.dwm-session.log" 2>&1
fi

exec /usr/local/bin/dwm >"$HOME/.dwm-session.log" 2>&1
