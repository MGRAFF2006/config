---
name: reviewable-pr
description: "Use when preparing, splitting, creating or updating a pull request, its title, description or review evidence."
---

# Make the change easy to review

When the repository is available, read its PR template, actual base and complete
diff. For an existing PR, read its description and discussion. A standalone
draft can use the supplied change summary; label unavailable verification.
Follow the shared
[development workflow](../../workflows/development.md) for scope, authorization,
attribution, independent review and merge conditions.

Lead with the concrete problem and resulting behavior. Keep one coherent
concern per PR; link independent follow-ups or stack prerequisite changes.
Use the detail needed to understand the change rather than a file-by-file
narrative or fixed word count.

Show comparable before/after evidence when it clarifies the behavior: the same
input/output scenario, a focused regression, paired screenshots or a recording.
Label inferred earlier behavior and missing captures. Use a small diagram when
relationships, dependencies or a sequence are easier to understand visually;
a diagram is optional, not a required section for every PR.

State actual validation results and material gaps. Keep long logs in accessible
artifacts or collapsed details. Never invent measurements or mark an unrun
check successful. Evidence published with a PR must be accessible to its readers.

Re-read the final diff and refresh the title, description and evidence when
the scope changes. Preserve useful human-written context. With `gh`, use a
body file to preserve Markdown. Register each PR you create, take over or push
to with T3's `link_pull_request` when exposed, following the current runtime's
linking and monitoring instructions.
