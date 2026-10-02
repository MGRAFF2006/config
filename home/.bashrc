# ~/.bashrc — themed fallback; the primary interactive shell is zsh.
[[ $- != *i* ]] && return

export COLORTERM=truecolor
export CLICOLOR=1

if command -v zsh &>/dev/null && [[ -z "${ZSH_VERSION:-}" ]]; then
  exec zsh
fi

if command -v starship &>/dev/null; then
  eval "$(starship init bash)"
fi
