# ─────────────────────────────────────────────
# laptop.zsh — Laptop (KDE) overrides
# Sourced only on hostname matching the laptop
# (Update the hostname check in .zshrc if needed)
# ─────────────────────────────────────────────

# KDE-specific helpers
alias kc='kdeconnect-cli'

# Screenshot with spectacle (KDE)
alias screenshot='spectacle -b -r -o ~/Pictures/screenshot_$(date +%Y%m%d_%H%M%S).png'

# Battery status
alias battery='cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1'

# npm global path (laptop)
export PATH="/home/humunkulud/.npm-global/bin:$PATH"
