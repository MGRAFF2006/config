---
name: write-agents-md
description: "Use when authoring or editing global agent instructions, project AGENTS.md or CLAUDE.md, or a project glossary."
---

# Write agent instructions (Theo-style)

## Pick the layer

- **Root instructions** → `~/Documents/config/agent/AGENTS.md`.
  All tool instruction links read the same file; there is no rendered copy.
  Keep preferences, permissions, and ownership principles in the root; put
  detailed procedures in linked `agent/workflows/` files. Preserve the user's
  stated preferences and make supporting guidance reachable from the root.
- **Project AGENTS.md** → repo root. How to *change* this codebase; not a README.

Theo: the value is the **process**, not copy-pasting his private letter.

## Root checklist

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
