---
name: audit-agent-failures
description: >-
  Mine recent agent/chat history for repeated failure modes and propose letter
  or AGENTS.md one-liners. Use when the user asks to audit agent mistakes,
  review thread history, tune the letter, or asks why agents keep failing.
---

# Audit agent failures (Theo's history pass)

Theo's letter video method: do not invent rules from vibes alone. Ask an agent to
scan real history for failure modes, then add **only** lines that earn tokens.

## Process

1. Scope: this repo's `.cursor` transcripts / agent logs if present, or the
   user's described failures. Prefer concrete threads over guesses.
2. Categorize (counts if possible):
   - wrong process kills / environment damage
   - unasked edits / overbuild
   - draft PRs / bad PR titles/bodies
   - repo-wide checks when focused would do
   - stopping early / no verify
   - glossary confusion (`user` vs maintainer)
   - laptop/desktop assumptions
3. For each top failure: propose **one** steering line for either:
   - global `~/Documents/config/agent/GLOBAL.md`, or
   - the project's `AGENTS.md`, or
   - a skill whose **description** is only trigger keywords
4. Prefer codebase/test fixes when the failure is a design smell.
5. Show before/after snippets. Do not paste Theo's private letter verbatim —
   copy the *process*, write humunkulud's words.

## Skill description reminder

Descriptions are **triggers**, not manuals. Prefer:

`Use when the user asks to monitor, watch, or babysit a PR.`

over a paragraph that already contains the whole skill.
