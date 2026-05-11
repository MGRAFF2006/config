# ~/.zshrc — humunkulud's ZSH config loader
# Part of ~/Documents/config — DO NOT EDIT DIRECTLY
# Edit files in ~/.config/zshrc/ instead

# If not running interactively, bail out
[[ $- != *i* ]] && return

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

# Load modular config (alphabetical order: 00, 10, 20, 30, 40, 50)
for _f in "$XDG_CONFIG_HOME"/zshrc/*.zsh; do
  [[ -f $_f ]] && source "$_f"
done
unset _f

# Load machine-specific overrides
# Priority: 1) hostname file, 2) MACHINE_TYPE env var, 3) auto-detect by hostname
_machine_type="${MACHINE_TYPE:-$(hostname)}"

# Auto-detection fallback: if hostname is the same on both (both 'archlinux'),
# detect by presence of KDE/plasma
if [[ "$_machine_type" == "archlinux" ]]; then
  if command -v plasmashell &>/dev/null || [[ -d /usr/lib/plasma-workspace ]]; then
    _machine_type="laptop"
  else
    _machine_type="archlinux"  # desktop/DWM
  fi
fi

_host_config="$XDG_CONFIG_HOME/zshrc.d/${_machine_type}.zsh"
[[ -f $_host_config ]] && source "$_host_config"
unset _host_config _machine_type

# Load any personal customizations (not tracked in git)
[[ -f ~/.zshrc_custom ]] && source ~/.zshrc_custom
