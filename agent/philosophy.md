# Agent markdown philosophy

Short reference when editing the global letter, project `AGENTS.md`, Cursor
rules, or skills. Drawn from Theo (t3.gg):

- *Delete your CLAUDE.md* — cut discoverable dumps; Band-Aid gotchas only
- *I made Claude smarter by writing it a letter* — global file is a **hand-written
  letter** (tone + alignment + glossary), not a rules encyclopedia
- live `pingdotgg/t3code` `AGENTS.md` — product non-negotiables, glossary,
  "ways to hurt yourself" from audited failures

## Two layers

| Layer | File | Job |
|-------|------|-----|
| **Letter (global)** | `agent/GLOBAL.md` (same source in every tool) | Who I am, tone match, default prefs, glossary, machines |
| **Project AGENTS.md** | repo root | How to change *this* codebase; landmines from real failures |

Agents did not author the letter. You (or I with you) edit it by hand when
preferences drift. Project files can be drafted with help, then you cut.

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
~/Documents/config/agent/GLOBAL.md          # instructions and letter
~/.cursor/rules/agent-kit.mdc -> …/GLOBAL.md
~/.agents/skills           -> …/skills
~/.claude/skills/<name>     -> …/skills/<name>
~/.codex/AGENTS.md         -> …/GLOBAL.md
~/.config/opencode/AGENTS.md -> …/GLOBAL.md
AGENTS.md (per repo)
CLAUDE.md -> AGENTS.md
```

## Personal kit

Canonical: `~/Documents/config/agent/` (desktop ↔ laptop via Syncthing).
Install only the kit: `bash ~/Documents/config/scripts/install-agent-kit.sh`.
Fleet documentation: [fleet/README.md](fleet/README.md).
