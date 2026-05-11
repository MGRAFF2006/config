if [[ -o interactive && -t 0 && -t 1 ]]; then
  bindkey '^H' backward-kill-word
  bindkey '^Z' undo
fi
