#!/usr/bin/env bash
# Symlink shared instructions and skills; leave authentication and runtime state local.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
agent_home="${AGENT_KIT_HOME:-$HOME}"
codex_root="${CODEX_HOME:-$agent_home/.codex}"
config_root="${XDG_CONFIG_HOME:-$agent_home/.config}"
mode="${1:-install}"
case "$mode" in
  install|--dry-run|--check) ;;
  *) echo "Usage: $0 [--dry-run|--check]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo "Expected at most one argument" >&2; exit 2; }

backup_root=""
failures=0
backup_path() {
  local dst="$1" relative
  if [[ -z "$backup_root" ]]; then
    mkdir -p -- "$agent_home/.local/share/agent-kit-backups"
    backup_root="$(mktemp -d "$agent_home/.local/share/agent-kit-backups/$(date +%Y%m%d-%H%M%S)-XXXXXX")"
  fi
  relative="${dst#"$agent_home"/}"
  [[ "$relative" != "$dst" ]] || relative="external$dst"
  mkdir -p -- "$(dirname -- "$backup_root/$relative")"
  mv -- "$dst" "$backup_root/$relative"
  echo "BACKUP $dst -> $backup_root/$relative"
}

link_path() {
  local src="$1" dst="$2"
  [[ -e "$src" ]] || { echo "Missing source: $src" >&2; exit 1; }
  if [[ -L "$dst" && "$(readlink -- "$dst")" == "$src" ]]; then
    [[ "$mode" != "--check" ]] || echo "OK $dst"
    return
  fi
  case "$mode" in
    --check)
      echo "MISSING or different link: $dst"
      failures=$((failures + 1)) ;;
    --dry-run) echo "LINK $dst -> $src (back up existing destination)" ;;
    install)
      mkdir -p -- "$(dirname -- "$dst")"
      if [[ -e "$dst" || -L "$dst" ]]; then backup_path "$dst"; fi
      ln -s -- "$src" "$dst"
      echo "LINK $dst -> $src" ;;
  esac
}

for target in "$agent_home/AGENTS.md" "$codex_root/AGENTS.md" \
  "$config_root/opencode/AGENTS.md" "$agent_home/.claude/CLAUDE.md" \
  "$agent_home/.claude/AGENTS.md"; do
  link_path "$repo_root/agent/GLOBAL.md" "$target"
done

# Linking the whole directory makes future shared skills available after sync.
link_path "$repo_root/agent/skills" "$agent_home/.agents/skills"
for skill in "$repo_root"/agent/skills/*; do
  [[ -f "$skill/SKILL.md" ]] || continue
  name="$(basename -- "$skill")"
  # Claude also writes account-downloaded skills here; keep its root machine-local.
  link_path "$skill" "$agent_home/.claude/skills/$name"
  # Retire only duplicate kit links, or a byte-identical old Codex skill copy.
  for legacy in "$agent_home/.cursor/skills/$name" "$codex_root/skills/$name"; do
    if [[ -L "$legacy" && "$(readlink -- "$legacy")" == "$skill" ]] || \
      { [[ -d "$legacy" && ! -L "$legacy" ]] && diff -qr -- "$legacy" "$skill" >/dev/null; }; then
      case "$mode" in
        install) backup_path "$legacy" ;;
        --dry-run) echo "RETIRE duplicate skill: $legacy (back up)" ;;
        --check) echo "DUPLICATE skill: $legacy"; failures=$((failures + 1)) ;;
      esac
    fi
  done
done

# Retire this kit's Cursor rules now that Cursor is no longer used.
for legacy in "$agent_home/.cursor/rules/agent-kit.mdc" \
  "$agent_home/.cursor/rules/letter.mdc" "$agent_home/.cursor/rules/personal-machines.mdc"; do
  if [[ -L "$legacy" && "$(readlink -f -- "$legacy")" == "$repo_root/agent/GLOBAL.md" ]]; then
    case "$mode" in
      install) backup_path "$legacy" ;;
      --dry-run) echo "RETIRE duplicate rule: $legacy (back up)" ;;
      --check) echo "DUPLICATE rule: $legacy"; failures=$((failures + 1)) ;;
    esac
  fi
done

if [[ "$mode" == "--check" ]]; then
  for tool in git ssh rsync tmux tailscale syncthing codex; do
    if command -v "$tool" >/dev/null 2>&1; then echo "OK $tool: $(command -v "$tool")"
    else echo "MISSING $tool"; failures=$((failures + 1)); fi
  done
  if command -v tailscale >/dev/null 2>&1; then tailscale status || failures=$((failures + 1)); fi
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user is-active syncthing.service || echo "CHECK: Syncthing user service is not active"
  fi
  exit "$((failures > 0))"
fi
[[ -z "$backup_root" ]] || echo "Previous files: $backup_root"
echo "Shared kit linked. Restart agent sessions to reload context."
