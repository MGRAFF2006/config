---
name: write-agents-md
description: >-
  Author or slim AGENTS.md or the global letter Theo-style. Use when creating
  AGENTS.md, rewriting agent.md/CLAUDE.md, writing a letter to the agent, or
  adding a glossary.
---

# Write AGENTS.md / letter (Theo-style)

## Pick the layer

- **Global instructions and letter** → `~/Documents/config/agent/GLOBAL.md`.
  All tool instruction links read the same file; there is no rendered copy.
  Preserve the user's stated preferences when editing the letter section.
- **Project AGENTS.md** → repo root. How to *change* this codebase; not a README.

Theo: the value is the **process**, not copy-pasting his private letter.

## Letter checklist

1. Introduce the human in first person; address the agent as "you".
2. State building taste (simple systems, YAGNI) so the model tone-matches.
3. Add 5–15 alignment bullets from **repeated** annoyances only.
4. Add a glossary if role words collide (`you` / `me` / `user` / `agent`).
5. Say prompts override the letter.
6. Keep it short enough to reread without skimming past.

## Project AGENTS.md checklist

1. Delete anything discoverable from manifests / `rg`.
2. Keep landmines, non-obvious commands, smallest-verification policy.
3. Optional glossary overrides for product vocabulary.
4. Optional skills index with trigger phrases.
5. If Claude compatibility is needed, link `CLAUDE.md` to `AGENTS.md` only after
   inspecting any existing file and preserving its unique content.
6. Cursor/Cloud-only notes → `.cursor/rules/*.mdc`, not AGENTS.md.

Skeleton: `~/Documents/config/agent/AGENTS.template.md`

## After failures

Use the `audit-agent-failures` skill. Add one line per repeated failure mode —
or fix the code instead.
