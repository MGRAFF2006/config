# ─────────────────────────────────────────────
# 50-tools.zsh — Tool integrations
# ─────────────────────────────────────────────

# zoxide (smarter cd with z/zi) — cached init
if command -v zoxide &>/dev/null; then
  _zoxide_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zoxide-init.zsh"
  _zoxide_bin="$(command -v zoxide)"
  if [[ ! -f "$_zoxide_cache" || "$_zoxide_bin" -nt "$_zoxide_cache" ]]; then
    mkdir -p "${_zoxide_cache:h}"
    zoxide init zsh > "$_zoxide_cache"
  fi
  source "$_zoxide_cache"
  unset _zoxide_cache _zoxide_bin
fi

# fzf keybindings + completions — cached init
if command -v fzf &>/dev/null; then
  _fzf_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/fzf-init.zsh"
  _fzf_bin="$(command -v fzf)"
  if [[ ! -f "$_fzf_cache" || "$_fzf_bin" -nt "$_fzf_cache" ]]; then
    mkdir -p "${_fzf_cache:h}"
    fzf --zsh > "$_fzf_cache" 2>/dev/null || {
      # Fallback for older fzf versions
      : > "$_fzf_cache"
      [ -f /usr/share/fzf/key-bindings.zsh ] && cat /usr/share/fzf/key-bindings.zsh >> "$_fzf_cache"
      [ -f /usr/share/fzf/completion.zsh ]   && cat /usr/share/fzf/completion.zsh >> "$_fzf_cache"
    }
  fi
  source "$_fzf_cache"
  unset _fzf_cache _fzf_bin
fi

# Ctrl+F → zi (zoxide interactive jump)
bindkey -s '^F' 'zi\n'

# Fastfetch on login shell only (not every subshell/terminal tab)
if command -v fastfetch &>/dev/null && [[ -o login ]] && [[ -t 0 && -t 1 ]]; then
  fastfetch --config "$XDG_CONFIG_HOME/fastfetch/config.jsonc" 2>/dev/null || fastfetch
fi

# GitHub CLI completions — cached init
if command -v gh &>/dev/null; then
  _gh_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/gh-completion.zsh"
  _gh_bin="$(command -v gh)"
  if [[ ! -f "$_gh_cache" || "$_gh_bin" -nt "$_gh_cache" ]]; then
    mkdir -p "${_gh_cache:h}"
    gh completion -s zsh > "$_gh_cache" 2>/dev/null
  fi
  source "$_gh_cache"
  unset _gh_cache _gh_bin
fi

# Docker completions (if not already handled by zsh-completions)
if [ -f /usr/share/zsh/site-functions/_docker ]; then
  autoload -Uz _docker
fi
