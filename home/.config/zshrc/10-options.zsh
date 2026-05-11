# ─────────────────────────────────────────────
# 10-options.zsh — Shell options & history
# ─────────────────────────────────────────────

# Completions
autoload -Uz compinit
compinit

# Case-insensitive tab completion
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

# Show completion list automatically
setopt AUTO_LIST
setopt COMPLETE_IN_WORD

# Directory options
setopt AUTO_CD           # type a dir name to cd into it
setopt AUTO_PUSHD        # cd pushes onto dir stack
setopt PUSHD_IGNORE_DUPS
setopt CDABLE_VARS

# Globbing
setopt EXTENDED_GLOB
setopt GLOB_DOTS         # dotfiles included in globs

# Misc
setopt INTERACTIVE_COMMENTS   # allow # comments in interactive shell
setopt CHECK_WINDOW_SIZE 2>/dev/null || true  # zsh does this automatically

# Ctrl+S for forward history search (disable flow control)
stty -ixon 2>/dev/null || true

# ── History ────────────────────────────────
HISTFILE="$HOME/.zsh_history"
HISTSIZE=1000000
SAVEHIST=1000000
setopt APPEND_HISTORY
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_REDUCE_BLANKS
setopt SHARE_HISTORY
setopt EXTENDED_HISTORY      # save timestamps

# Ignore common throwaway commands from history
export HISTIGNORE="ls:cd:cd ..:pwd:exit:clear:history"
