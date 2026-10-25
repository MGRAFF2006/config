# Agent kit

[AGENTS.md](AGENTS.md) is the root: Mathis's preferences, permissions, ownership
principles, and directions to the relevant branch. Every supported local tool
reads that same source through a symlink. Supporting documents expand the root;
they do not grant broader permissions. Read them when their task applies.

## Follow the tree

- [Delegation](workflows/delegation.md): assign problems, coordinate children,
  route questions through the interaction thread, integrate, and verify outcomes.
- [Decisions](workflows/decisions.md): use context, explore reversible options,
  safeguard hard-to-reverse actions, and bring evidence for Mathis's decisions.
- [Development](workflows/development.md): implementation, verification, and
  GitHub work and review history.
- [Environment](workflows/environment.md): host selection, system work, long
  jobs, and native GUI isolation. [Fleet](fleet/README.md) holds machine records
  and operating procedures.
- [Personal routines](workflows/personal.md): account access, mail, and briefings.
- [Skills](skills/): specialized workflows selected by their descriptions.
  [Source metadata](skills/SOURCES.json) records provenance for adapted skills.
- Project `AGENTS.md` files add local instructions. The
  [project template](AGENTS.template.md), [writing skill](skills/write-agents-md/SKILL.md),
  and [authoring reference](philosophy.md) support instruction maintenance.

## Instruction layers and origins

| Source | Owns | Maintained in |
| --- | --- | --- |
| Platform, harness and T3 integration | Runtime rules, tools and permissions | The running product; outside this kit |
| Mathis's current request | Task outcome, steering and explicit authorization | The conversation |
| Shared root | Personal defaults, boundaries and ownership principles | `agent/AGENTS.md` |
| Project or nested `AGENTS.md` | Repository-specific behavior | The relevant project |
| Linked workflows and skills | Procedures selected for the current task | `agent/workflows/` and `agent/skills/` |
| Fleet records and dated handoffs | Host facts and task-specific historical state | `agent/fleet/` |

The root is Mathis's instruction set, refined with agent assistance from actual
tasks and explicit decisions. Public methods from Theo, Dara, Matt Pocock and
others informed adaptations; this is not a copy of anyone's private letter.
The [authoring reference](philosophy.md) explains the approach.

[SOURCES.json](skills/SOURCES.json) lists every shared skill and its provenance:
personal adaptations, Anthropic document/frontend skills, Vercel React skills,
and the adapted effective-html skill. Recorded revisions identify imports;
local changes are intentional. Frontend's fetched revision and Ponytail's
external origin are unrecorded and remain explicit gaps.

Provider/system and plugin skills are separate. Codex's `.system` skills,
Cursor's `skills-cursor`, and skills in a plugin cache are provider-managed;
do not copy them into this tree. A cached file does not establish that a plugin
is enabled or that a runtime advertised its skill. Names and descriptions are
available for selection; skill bodies and references are loaded when needed.
Linking a document does not automatically load it or change its authority.
Authentication, chats, provider settings and app databases stay local.

Research and historical records live under Fleet, including its
[research notes](fleet/RESEARCH.md) and
[dated task handoffs](fleet/WORKFLOW.md#dated-task-handoffs). Treat these as background
evidence, not new authorization. Existing task-specific holds remain relevant
when resuming that task.

## Install the entrypoints

Syncthing distributes the repo; the installer recreates links using each
computer's own checkout path.

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
| `~/AGENTS.md` | `agent/AGENTS.md` |
| `~/.codex/AGENTS.md` | `agent/AGENTS.md` |
| `~/.config/opencode/AGENTS.md` | `agent/AGENTS.md` |
| `~/.claude/CLAUDE.md` | `agent/AGENTS.md` |
| `~/.claude/AGENTS.md` | `agent/AGENTS.md` |
| `~/.agents/skills` | Entire `agent/skills` directory |
| `~/.claude/skills/<name>` | Each corresponding shared skill directory |

`GLOBAL.md`, `PERSONAL.md`, and `LETTER.md` are compatibility symlinks to
`AGENTS.md`, so older machine links and historical references still work.
They are aliases, not additional instruction sources. There is no generated
copy to keep in sync.
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
Validate the kit with `python scripts/check-agent-kit.py` and
`shellcheck scripts/install-agent-kit.sh` from the repo root. The executable
check exercises installation with temporary files and stubbed services, verifies
the shared source registry, and checks the maintained instruction links. It makes
no model calls and does not prove that an agent will interpret the wording well.
