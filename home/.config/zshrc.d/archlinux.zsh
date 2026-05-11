# ─────────────────────────────────────────────
# archlinux.zsh — Desktop (DWM) overrides
# Sourced only on hostname: archlinux
# ─────────────────────────────────────────────

# Monitor resolution shortcuts (DWM multi-monitor)
alias res1='xrandr --output DisplayPort-0 --mode 2560x1440 --rate 155'
alias res2='xrandr --output DisplayPort-0 --mode 1920x1080 --rate 120'
alias res-dual='xrandr --output DisplayPort-0 --mode 2560x1440 --rate 155 --output HDMI-A-0 --mode 1920x1080 --rate 74.97 --right-of DisplayPort-0'

# German keyboard layout
alias setkb='setxkbmap de && echo "Keyboard set to de."'

# DWM restart (kill X and let xinit restart)
alias dwm-restart='kill -HUP $(pgrep -x dwm)'

# Start X manually (DWM)
alias startx-dwm='startx ~/.xinitrc'

# npm global path (desktop)
export PATH="/home/humunkulud/.npm-global/bin:$PATH"
