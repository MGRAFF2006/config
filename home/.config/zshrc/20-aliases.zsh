# ─────────────────────────────────────────────
# 20-aliases.zsh — All aliases
# ─────────────────────────────────────────────

# ── Modern CLI replacements ─────────────────
command -v rg    &>/dev/null && alias grep='rg'
command -v bat   &>/dev/null && alias cat='bat'
command -v eza   &>/dev/null && {
  alias ls='eza -a --icons=always'
  alias ll='eza -al --icons=always --git'
  alias lt='eza -a --tree --level=2 --icons=always'
  alias la='eza -al --icons=always'
  alias lx='eza -al --sort=extension --icons=always'
  alias lk='eza -al --sort=size --icons=always'
  alias lc='eza -al --sort=changed --icons=always'
  alias lu='eza -al --sort=accessed --icons=always'
  alias lr='eza -al --recurse --icons=always'
  alias lm='eza -al --icons=always | more'
  alias lw='eza -al --icons=always'
  alias labc='eza -al --sort=name --icons=always'
  alias ldir='eza -al --only-dirs --icons=always'
  alias lf='eza -al --only-files --icons=always'
}

# Safe delete — use \rm or /bin/rm for real rm
command -v trash &>/dev/null && alias rm='trash -v'

# ── Editor ──────────────────────────────────
alias vim='nvim'
alias vi='nvim'
alias v='nvim'
alias svi='sudoedit'
alias snano='sudo nano'

# ── Navigation ──────────────────────────────
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias cd..='cd ..'
alias home='cd ~'
alias bd='cd "$OLDPWD"'

# ── General utilities ───────────────────────
alias c='clear'
alias cls='clear'
alias da='date "+%Y-%m-%d %A %T %Z"'
alias cp='cp -i'
alias mv='mv -i'
alias mkdir='mkdir -p'
alias ps='ps auxf'
alias ping='ping -c 10'
alias less='less -R'
alias rmd='/bin/rm --recursive --force --verbose'

# ── File search helpers ─────────────────────
alias h='history | grep'
alias p='ps aux | grep'
alias topcpu='/bin/ps -eo pcpu,pid,user,args | sort -k 1 -r | head -10'
alias f='find . | grep'
alias countfiles='for t in files links directories; do echo "$(find . -type ${t:0:1} | wc -l) $t"; done 2>/dev/null'
alias checkcommand='type -a'
alias openports='netstat -nape --inet'

# ── Disk / mounts ───────────────────────────
alias diskspace='du -S | sort -n -r | more'
alias folders='du -h --max-depth=1'
alias folderssort='find . -maxdepth 1 -type d -print0 | xargs -0 du -sk | sort -rn'
alias treed='tree -CAFd'
alias mountedinfo='df -hT'

# ── Archives ────────────────────────────────
alias mktar='tar -cvf'
alias mkbz2='tar -cvjf'
alias mkgz='tar -cvzf'
alias untar='tar -xvf'
alias unbz2='tar -xvjf'
alias ungz='tar -xvzf'

# ── chmod shortcuts ─────────────────────────
alias mx='chmod a+x'
alias 000='chmod -R 000'
alias 644='chmod -R 644'
alias 666='chmod -R 666'
alias 755='chmod -R 755'
alias 777='chmod -R 777'

# ── SHA ─────────────────────────────────────
alias sha1='openssl sha1'

# ── Docker ──────────────────────────────────
alias docker-clean='docker container prune -f; docker image prune -f; docker network prune -f; docker volume prune -f'

# ── Git shortcuts ───────────────────────────
alias dots='git --git-dir=$HOME/Documents/config/.git --work-tree=$HOME/Documents/config'

# ── System ──────────────────────────────────
alias rebootsafe='sudo shutdown -r now'
alias rebootforce='sudo shutdown -r -n now'
alias update-grub='sudo grub-mkconfig -o /boot/grub/grub.cfg'
alias logs='sudo find /var/log -type f -exec file {} \; | grep "text" | cut -d" " -f1 | sed -e "s/:$//g" | grep -v "[0-9]$" | xargs tail -f'

# ── pacman / yay helpers ─────────────────────
alias yayf="yay -Slq | fzf --multi --preview 'yay -Sii {1}' --preview-window=down:75% | xargs -ro yay -S"
alias nf='fastfetch'
alias ff='fastfetch'

# ── Services ────────────────────────────────
alias hug='systemctl --user restart hugo'
alias lanm='systemctl --user restart lan-mouse'

# ── Misc ────────────────────────────────────
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history | tail -n1 | sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
alias whatismyip='whatsmyip'
alias wifi='nmtui'
