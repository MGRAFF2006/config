# Agent markdown philosophy

Short reference when editing the global letter, project `AGENTS.md`, Cursor
rules, or skills. Drawn from Theo (t3.gg):

The [root instructions](AGENTS.md) define the current structure. This reference
guides authoring; it does not add a separate layer of operating permissions.

- *Delete your CLAUDE.md* — cut discoverable dumps; Band-Aid gotchas only
- *I made Claude smarter by writing it a letter* — global file is a **hand-written
  letter** (tone + alignment + glossary), not a rules encyclopedia
- live `pingdotgg/t3code` `AGENTS.md` — product non-negotiables, glossary,
  "ways to hurt yourself" from audited failures

## Two layers

| Layer | File | Job |
|-------|------|-----|
| **Root** | `agent/AGENTS.md` (same source in every tool) | Preferences, permissions, ownership principles, and navigation to detailed branches |
| **Project AGENTS.md** | repo root | How to change *this* codebase; landmines from real failures |

The root records Mathis's preferences, refined with agent assistance from actual
tasks and explicit decisions. It is a personal adaptation of public methods;
it is not Theo's private letter. Preserve Mathis's intent when editing it.

## Hierarchy of fixes (prefer earlier)

1. **Shape the codebase** so the right path is obvious.
2. **Attach checks** to commands the agent already runs.
3. **Add a focused test** as proof.
4. **Only then** add a line to the letter / `AGENTS.md` / a skill.

## Letter rules (global)

- Write like a person introducing themselves; models **tone-match**.
- Call out anti-patterns you actually see (overeager coding, editing on
  questions, subagent spam) in a few sentences — not a manifesto.
- Include a **glossary** when the same English word means two roles.
- Explicitly allow the live prompt to override the letter.
- Do **not** paste someone else's letter; steal the process.

## Project AGENTS.md rules

| Keep | Cut |
|------|-----|
| Repeated wrong tool/command choices | Stack overview the model can discover |
| Landmines ("never kill by pattern") | Default language style guides |
| Smallest-verification policy | Full file trees / `/init` essays |
| Glossary overrides for *this* product | Duplicate of README |
| Skill pointers with trigger phrases | Always-on procedure dumps |

## Skills

- Descriptions are **triggers** ("Use when…"), always in context — keep them short.
- Bodies hold the procedure; load on demand.
- Universal skills live in `agent/skills/` (Syncthing), installed to
  `~/.agents/skills/`. Machine facts live in `agent/fleet/machines/`; add
  machine-specific skill folders only when an actual workflow needs them.
- Split "file PR" vs "babysit PR" style skills when triggers differ.

## Cross-tool layout

```
~/Documents/config/agent/AGENTS.md          # canonical root
~/Documents/config/agent/workflows/        # task-specific procedures
~/AGENTS.md                -> …/agent/AGENTS.md
~/.agents/skills           -> …/skills
~/.claude/skills/<name>     -> …/skills/<name>
~/.codex/AGENTS.md         -> …/agent/AGENTS.md
~/.config/opencode/AGENTS.md -> …/agent/AGENTS.md
AGENTS.md (per repo)
CLAUDE.md -> AGENTS.md
```

## Personal kit

Canonical: `~/Documents/config/agent/` (desktop ↔ laptop via Syncthing).
Install only the kit: `bash ~/Documents/config/scripts/install-agent-kit.sh`.
Fleet documentation: [fleet/README.md](fleet/README.md).
