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

# Load machine-specific overrides by hostname
_host_config="$XDG_CONFIG_HOME/zshrc.d/$(hostname).zsh"
[[ -f $_host_config ]] && source "$_host_config"
unset _host_config

# Load any personal customizations (not tracked in git)
[[ -f ~/.zshrc_custom ]] && source ~/.zshrc_custom
