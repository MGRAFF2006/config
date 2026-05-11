# ─────────────────────────────────────────────
# 00-init.zsh — Environment & PATH
# ─────────────────────────────────────────────

# XDG Base Directories
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CACHE_HOME="$HOME/.cache"

# Editor
export EDITOR=nvim
export VISUAL=nvim
export SUDO_EDITOR="$HOME/.local/bin/nvim"
export PAGER=less

# PATH — ordered by priority
typeset -U path  # zsh: deduplicate PATH entries automatically
path=(
  "$HOME/.local/bin"
  "$HOME/.opencode/bin"
  "$HOME/.cargo/bin"
  "$HOME/.npm-global/bin"
  "/var/lib/flatpak/exports/bin"
  "$HOME/.local/share/flatpak/exports/bin"
  $path
)
export PATH

# Colors for ls / grep
export CLICOLOR=1
export LS_COLORS='no=00:fi=00:di=00;34:ln=01;36:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arj=01;31:*.taz=01;31:*.lzh=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.gz=01;31:*.bz2=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.png=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.avi=01;35:*.mkv=01;35:*.flac=01;35:*.mp3=01;35:*.wav=01;35:*.ogg=01;35:*.xml=00;31:'

# Colored man pages (Nord-inspired)
export LESS_TERMCAP_mb=$'\E[01;31m'
export LESS_TERMCAP_md=$'\E[01;34m'
export LESS_TERMCAP_me=$'\E[0m'
export LESS_TERMCAP_se=$'\E[0m'
export LESS_TERMCAP_so=$'\E[01;44;33m'
export LESS_TERMCAP_ue=$'\E[0m'
export LESS_TERMCAP_us=$'\E[01;36m'
