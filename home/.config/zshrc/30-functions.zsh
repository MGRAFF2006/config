# ─────────────────────────────────────────────
# 30-functions.zsh — Shell functions
# ─────────────────────────────────────────────

# Extract any archive
extract() {
  for archive in "$@"; do
    if [ -f "$archive" ]; then
      case $archive in
        *.tar.bz2) tar xvjf "$archive" ;;
        *.tar.gz)  tar xvzf "$archive" ;;
        *.bz2)     bunzip2 "$archive" ;;
        *.rar)     rar x "$archive" ;;
        *.gz)      gunzip "$archive" ;;
        *.tar)     tar xvf "$archive" ;;
        *.tbz2)    tar xvjf "$archive" ;;
        *.tgz)     tar xvzf "$archive" ;;
        *.zip)     unzip "$archive" ;;
        *.Z)       uncompress "$archive" ;;
        *.7z)      7z x "$archive" ;;
        *) echo "Don't know how to extract '$archive'" ;;
      esac
    else
      echo "'$archive' is not a valid file!"
    fi
  done
}

# Search text in all files in current dir
ftext() {
  grep -iIHrn --color=always "$1" . | less -r
}

# Copy file with progress bar
cpp() {
  set -e
  strace -q -ewrite cp -- "${1}" "${2}" 2>&1 | awk '{
    count += $NF
    if (count % 10 == 0) {
      percent = count / total_size * 100
      printf "%3d%% [", percent
      for (i=0;i<=percent;i++) printf "="
      printf ">"
      for (i=percent;i<100;i++) printf " "
      printf "]\r"
    }
  } END { print "" }' total_size="$(stat -c '%s' "${1}")" count=0
}

# Copy and go to directory
cpg() {
  if [ -d "$2" ]; then
    cp "$1" "$2" && cd "$2"
  else
    cp "$1" "$2"
  fi
}

# Move and go to directory
mvg() {
  if [ -d "$2" ]; then
    mv "$1" "$2" && cd "$2"
  else
    mv "$1" "$2"
  fi
}

# Create and go to directory
mkdirg() {
  mkdir -p "$1"
  cd "$1"
}

# Go up N directories
up() {
  local d=""
  local limit=$1
  for ((i = 1; i <= limit; i++)); do
    d="$d/.."
  done
  d=$(echo "$d" | sed 's/^\///')
  [ -z "$d" ] && d=..
  cd "$d"
}

# Automatically ls after cd / zoxide
cd() {
  if [ -n "$1" ]; then
    builtin cd "$@" && ls
  else
    builtin cd ~ && ls
  fi
}

# Last 2 fields of working directory
pwdtail() {
  pwd | awk -F/ '{nlast = NF -1; print $nlast"/"$NF}'
}

# Detect distribution
distribution() {
  local dtype="unknown"
  if [ -r /etc/os-release ]; then
    source /etc/os-release
    case $ID in
      fedora|rhel|centos) dtype="redhat" ;;
      sles|opensuse*)     dtype="suse" ;;
      ubuntu|debian)      dtype="debian" ;;
      gentoo)             dtype="gentoo" ;;
      arch|manjaro)       dtype="arch" ;;
      slackware)          dtype="slackware" ;;
      *)
        if [ -n "$ID_LIKE" ]; then
          case $ID_LIKE in
            *fedora*|*rhel*|*centos*) dtype="redhat" ;;
            *sles*|*opensuse*)        dtype="suse" ;;
            *ubuntu*|*debian*)        dtype="debian" ;;
            *gentoo*)                 dtype="gentoo" ;;
            *arch*)                   dtype="arch" ;;
            *slackware*)              dtype="slackware" ;;
          esac
        fi ;;
    esac
  fi
  echo "$dtype"
}

# Show OS version
ver() {
  local dtype
  dtype=$(distribution)
  case $dtype in
    redhat)    cat /etc/redhat-release 2>/dev/null || cat /etc/issue; uname -a ;;
    suse)      cat /etc/SuSE-release ;;
    debian)    lsb_release -a ;;
    gentoo)    cat /etc/gentoo-release ;;
    arch)      cat /etc/os-release ;;
    slackware) cat /etc/slackware-version ;;
    *)         cat /etc/issue 2>/dev/null || echo "Unknown distribution" ;;
  esac
}

# IP address lookup
whatsmyip() {
  echo -n "Internal IP: "
  ip addr show 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1
  echo -n "External IP: "
  curl -4 -s ifconfig.me
  echo
}

# Upload file to hastebin
hb() {
  if [ $# -eq 0 ]; then echo "No file path specified."; return; fi
  if [ ! -f "$1" ]; then echo "File path does not exist."; return; fi
  local uri="http://bin.christitus.com/documents"
  local response
  response=$(curl -s -X POST -d @"$1" "$uri")
  if [ $? -eq 0 ]; then
    local hasteKey
    hasteKey=$(echo "$response" | jq -r '.key')
    echo "http://bin.christitus.com/$hasteKey"
  else
    echo "Failed to upload the document."
  fi
}

# sudo nvim with your config preserved
svim() {
  sudo -E "$HOME/.local/bin/nvim" \
    --cmd "set runtimepath^=$HOME/.config/nvim runtimepath+=$HOME/.config/nvim/after" \
    --cmd "let g:loaded_remote_plugins=1" \
    -u "$HOME/.config/nvim/init.lua" "$@"
}

# Quick git commit
gcom() {
  git add .
  git commit -m "$1"
}

# Quick git push
lazyg() {
  git add .
  git commit -m "$1"
  git push
}

# Trim whitespace
trim() {
  local var=$*
  var="${var#"${var%%[![:space:]]*}"}"
  var="${var%"${var##*[![:space:]]}"}"
  echo -n "$var"
}

# Install shell support tools (arch)
install_shell_support() {
  local dtype
  dtype=$(distribution)
  case $dtype in
    arch) sudo pacman -S --needed zoxide trash-cli fzf bash-completion fastfetch starship eza bat ripgrep ;;
    debian) sudo apt-get install -y zoxide trash-cli fzf bash-completion fastfetch ;;
    *) echo "Unsupported distribution for auto-install" ;;
  esac
}
