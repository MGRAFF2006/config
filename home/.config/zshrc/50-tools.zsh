# ─────────────────────────────────────────────
# 50-tools.zsh — Tool integrations
# ─────────────────────────────────────────────

# zoxide (smarter cd with z/zi)
if command -v zoxide &>/dev/null; then
  eval "$(zoxide init zsh)"
fi

# fzf keybindings + completions
if command -v fzf &>/dev/null; then
  source <(fzf --zsh) 2>/dev/null || {
    # Fallback for older fzf versions
    [ -f /usr/share/fzf/key-bindings.zsh ]    && source /usr/share/fzf/key-bindings.zsh
    [ -f /usr/share/fzf/completion.zsh ]       && source /usr/share/fzf/completion.zsh
  }
fi

# Ctrl+F → zi (zoxide interactive jump)
bindkey -s '^F' 'zi\n'

# Fastfetch on interactive terminal start
if command -v fastfetch &>/dev/null && [[ -o interactive ]] && [[ -t 0 && -t 1 ]]; then
  fastfetch --config "$XDG_CONFIG_HOME/fastfetch/config.jsonc" 2>/dev/null || fastfetch
fi

# GitHub CLI completions
if command -v gh &>/dev/null; then
  eval "$(gh completion -s zsh)" 2>/dev/null
fi

# Docker completions (if not already handled by zsh-completions)
if [ -f /usr/share/zsh/site-functions/_docker ]; then
  autoload -Uz _docker
fi
