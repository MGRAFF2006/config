#!/usr/bin/env bash
set -euo pipefail
[[ $(hostname -s) == homelab-dev && $(id -un) == humunkulud ]]
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$HOME/.cargo/bin:$PATH"
sudo apt-get update -qq
mapfile -t packages < <(awk '{sub(/#.*/, ""); if (NF) print $1}' "$repo/packages/debian-homelab-dev.txt")
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
mkdir -p "$HOME/.local/bin" "$HOME/.config/mise" "$HOME/.config/zshrc.d" "$HOME/Projects"
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
curl -fsSL https://github.com/jdx/mise/releases/download/v2026.10.0/mise-v2026.10.0-linux-x64.tar.gz -o "$temporary/mise.tar.gz"
tar -xzf "$temporary/mise.tar.gz" -C "$temporary"
install "$temporary/mise/bin/mise" "$HOME/.local/bin/mise"
curl -fsSL https://github.com/astral-sh/uv/releases/download/0.12.22/uv-x86_64-unknown-linux-gnu.tar.gz -o "$temporary/uv.tar.gz"
tar -xzf "$temporary/uv.tar.gz" -C "$temporary"
install "$temporary/uv-x86_64-unknown-linux-gnu/uv" "$temporary/uv-x86_64-unknown-linux-gnu/uvx" "$HOME/.local/bin/"
curl -fsSL https://github.com/neovim/neovim/releases/download/v0.12.5/nvim-linux-x86_64.tar.gz -o "$temporary/nvim.tar.gz"
mkdir -p "$HOME/.local/share/nvim-runtime"
tar -xzf "$temporary/nvim.tar.gz" -C "$HOME/.local/share/nvim-runtime" --strip-components=1
ln -sfn "$HOME/.local/share/nvim-runtime/bin/nvim" "$HOME/.local/bin/nvim"
curl -fsSL https://github.com/starship/starship/releases/download/v1.26.0/starship-x86_64-unknown-linux-musl.tar.gz -o "$temporary/starship.tar.gz"
tar -xzf "$temporary/starship.tar.gz" -C "$temporary"
install "$temporary/starship" "$HOME/.local/bin/starship"
if ! command -v rustup >/dev/null 2>&1; then
  curl -fsSL https://sh.rustup.rs -o "$temporary/rustup.sh"
  sh "$temporary/rustup.sh" -y --profile minimal --no-modify-path --default-toolchain 1.99.0
fi

bash "$repo/scripts/link-home.sh" homelab-dev
mise trust "$repo/headless/mise.toml"
mise install
mise reshim
uv python install 3.12
sudo chsh -s /usr/bin/zsh humunkulud
bash "$repo/scripts/install-agent-kit.sh" --check
if [[ ! -f "$HOME/.ssh/id_ed25519_github" ]]; then
  ssh-keygen -q -t ed25519 -N '' -C homelab-dev -f "$HOME/.ssh/id_ed25519_github"
fi
if ! ssh-keygen -F github.com >/dev/null; then
  curl -fsSL https://api.github.com/meta | python3 -c 'import json,sys; print("\n".join("github.com "+k for k in json.load(sys.stdin)["ssh_keys"]))' >> "$HOME/.ssh/known_hosts"
  chmod 600 "$HOME/.ssh/known_hosts"
fi
printf 'Development setup complete. GitHub public key needs authorization; secrets remain machine-local.\n'
