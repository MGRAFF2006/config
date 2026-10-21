---
name: prune-agent-context
description: >-
  Audit and shrink AGENTS.md, CLAUDE.md, Cursor rules, and personal skills that
  waste context or conflict. Use when agents feel slow/confused, after a model
  upgrade, or when the user asks to prune rules, delete CLAUDE.md bloat, or
  ablate agent context.
---

# Prune agent context

## When to run

- New model release ("delete half and see")
- Agents explore forever or pick legacy APIs
- Multiple overlapping instruction files disagree

## Audit checklist

For each unique always-on source (`GLOBAL.md`, project `AGENTS.md`/`CLAUDE.md`,
Cursor user rules, `.cursor/rules` with `alwaysApply: true`):

1. **Discoverable?** → delete (model can `rg` / read manifests).
2. **Stale?** → delete or fix the codebase instead.
3. **Task-specific?** → move to a skill or a glob-scoped rule.
4. **Enforcement?** → prefer a script/hook/test over prose.
5. **Duplicate?** → one source of truth; symlink the rest.
6. **Letter vs project?** → tone/prefs/glossary defaults stay in the letter;
   repo landmines stay in project `AGENTS.md`.

## Ablation loop

1. Back up the file (`cp AGENTS.md AGENTS.md.bak`).
2. Remove half (or everything except Do/Don't + Gotchas).
3. Re-run a representative task cold.
4. Add back **only** lines that prevented a real failure twice.
5. Delete the backup when stable.

## Skills hygiene

- Keep `~/.cursor/skills-cursor/` alone (Cursor-managed).
- Personal skills live in `~/.agents/skills/` → this kit under
  `~/Documents/config/agent/skills/`.
- Drop skills that are never triggered or that only restate language defaults.
- Descriptions must include **Use when…**; third person; under ~40 words of trigger signal.

## Machines

Tailscale names are `desktop` and `laptop`. Kit syncs via Syncthing
(`Documents/config`). Verify reachability and use an available suitable host;
new shared skills appear after sync. Rerun `install-agent-kit.sh` for new
Claude compatibility links.
