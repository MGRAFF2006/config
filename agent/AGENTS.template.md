# AGENTS.md

The role of this file is how agents **change this codebase** — common mistakes
and confusion points — not a second README. Global tone/prefs live in the
letter (`~/Documents/config/agent/GLOBAL.md`).

If something here is discoverable from the code or manifests, delete it. If
something **surprises** you, alert the developer and propose a one-line gotcha;
prefer a codebase/test fix when the surprise is a design smell.

## Glossary (only if words collide here)

| Term | Means |
|------|--------|
| **you** | the agent changing this repo |
| **we / maintainers** | humans who own this project |
| **user** | end-user of *this product* (not the maintainer) |

## Do

- Prefer the smallest verification that proves the change (focused test / lint / typecheck).
- Leave unrelated work untouched. Do not commit or push unless asked.

## Don't

- Do not run the full workspace test/lint/typecheck suite unless asked. CI owns that.
- Do not invent parallel docs (`ARCHITECTURE.md`, second READMEs) unless asked.
- Do not put secrets, machine-local absolute paths, or live data files in git.

## Gotchas

<!-- Add only repeated failure modes ("ways to hurt yourself"), from audits. -->

- _(none yet — add after the second time an agent fails the same way)_

## Skills

<!-- Trigger phrases only. Omit if empty. -->
