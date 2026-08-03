# ─────────────────────────────────────────────
# 40-prompt.zsh — Starship prompt (Nord theme)
# ─────────────────────────────────────────────

# Cache starship init to avoid subprocess on every shell start
if command -v starship &>/dev/null; then
  _starship_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/starship-init.zsh"
  _starship_bin="$(command -v starship)"
  if [[ ! -f "$_starship_cache" || "$_starship_bin" -nt "$_starship_cache" ]]; then
    mkdir -p "${_starship_cache:h}"
    starship init zsh > "$_starship_cache"
  fi
  source "$_starship_cache"
  unset _starship_cache _starship_bin
fi
