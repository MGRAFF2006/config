---
name: prune-agent-context
description: "Use when auditing or simplifying AGENTS.md, CLAUDE.md, rules or skills that are redundant, stale or conflicting."
---

# Keep instructions that change decisions

Inventory the actual instruction entrypoints and resolve symlinks before
counting sources. Distinguish the shared root, project rules, task workflows,
provider-managed skills and plugin instructions. A file present at several
paths is not proof that a runtime loaded it several times.

For each instruction, ask whether it preserves a preference or boundary,
prevents a demonstrated mistake, duplicates another source, or merely describes
discoverable code. Keep permissions and ownership principles in the root;
put operational detail in the relevant workflow and machine facts in Fleet.
Prefer a code, type or executable-check fix when it can prevent the mistake.

Preserve a recoverable baseline, remove or consolidate a concrete source of
noise, then try a representative task in a fresh context when behavioral
validation is useful. Compare scope, decisions, interruptions and evidence.
Restore guidance when the result demonstrates a need. A shorter file or a new
model alone does not justify deleting safeguards or half the instructions.

Keep skill descriptions concise and selective, with the procedure in the body.
Reconcile conflicting defaults rather than accumulating exceptions. Missing
invocation telemetry alone does not prove that a skill is unused.

Edit shared skills in this kit. Leave provider-managed directories such as
`~/.cursor/skills-cursor/` and Codex's `.system` skills to their provider.
Use the [kit installer](../../README.md#install-the-entrypoints) and verify
the result on each intended host without assuming synchronization completed.
