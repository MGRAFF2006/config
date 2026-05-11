#!/bin/sh
# ~/.xinitrc — Desktop (DWM) X11 startup
# Managed by ~/Documents/config

# Ensure /usr/local/bin is in PATH for locally built DWM
export PATH="/usr/local/bin:$PATH"

# Set cursor theme
xsetroot -cursor_name left_ptr &

# Load X resources
[ -f ~/.Xresources ] && xrdb -merge ~/.Xresources

# Multi-monitor layout (adjust to your display setup)
xrandr --output DisplayPort-0 --mode 2560x1440 --rate 155 \
       --output HDMI-A-0 --mode 1920x1080 --rate 74.97 --right-of DisplayPort-0 \
  2>/dev/null || true

# Start notification daemon
dunst &

# Start compositor (picom for transparency/blur)
picom --daemon 2>/dev/null &

# Set wallpaper
command -v feh &>/dev/null && feh --bg-scale ~/wallpaper/$(ls ~/wallpaper/ 2>/dev/null | head -1) 2>/dev/null &

# Start DWM — prefer locally built, fall back to /usr/local
if [ -x "$HOME/dwm/dwm" ]; then
  exec "$HOME/dwm/dwm" >"$HOME/.dwm-session.log" 2>&1
fi

exec /usr/local/bin/dwm >"$HOME/.dwm-session.log" 2>&1
