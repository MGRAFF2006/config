# Shared AI configuration

Edit [GLOBAL.md](GLOBAL.md) for personal instructions and communication
preferences, and `skills/` for reusable workflows. Every supported local tool
reads these same source files through symlinks. Syncthing distributes the repo;
the installer recreates links using each computer's own checkout path.

```bash
cd ~/Documents/config
./scripts/install-agent-kit.sh
./scripts/install-agent-kit.sh --check
```

Use `--dry-run` to preview. Existing files and directories are backed up under
`~/.local/share/agent-kit-backups/`; review any unique local skills there before
adding them to the shared kit. Installation is repeatable and does not rewrite
source files, install packages, or change services.

| Destination | Shared source |
| --- | --- |
| `~/AGENTS.md` | `agent/GLOBAL.md` |
| `~/.codex/AGENTS.md` | `agent/GLOBAL.md` |
| `~/.config/opencode/AGENTS.md` | `agent/GLOBAL.md` |
| `~/.claude/CLAUDE.md` | `agent/GLOBAL.md` |
| `~/.agents/skills` | Entire `agent/skills` directory |
| `~/.claude/skills/<name>` | Each corresponding shared skill directory |

`PERSONAL.md` and `LETTER.md` are relative compatibility symlinks to `GLOBAL.md`,
so older machine links still work during migration. There is no generated copy
to keep in sync.
The installer retires this kit's old duplicate rules and skill copies while
preserving unrelated files and Codex's managed `.system` skills.

Instructions and existing skill edits appear after sync; restart sessions as
needed. New skills appear through the shared directory for Codex and
OpenCode without reinstalling. Rerun the installer for Claude's new per-skill
links: its skill root stays local because Claude also writes account-downloaded
skills there. [Claude documents that separate state](https://code.claude.com/docs/en/skills).

Authentication, chats, provider settings, and app databases stay local. This
setup shares agent instructions and skills; each tool retains its own supported
runtime configuration format. Custom `CODEX_HOME` and `XDG_CONFIG_HOME` are
respected. Project conventions stay in the project's own `AGENTS.md`.

See [Fleet](fleet/README.md) for daily workflow, machine records, and onboarding.
Validate installer changes with `python scripts/check-agent-kit.py` and
`shellcheck scripts/install-agent-kit.sh` from the repo root. The executable
check uses temporary files and stubbed services without model calls.
