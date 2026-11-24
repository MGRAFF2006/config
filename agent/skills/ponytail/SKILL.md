---
name: ponytail
description: "Use when writing, fixing, reviewing or designing code, choosing dependencies, or when Mathis asks for a simpler solution, YAGNI or lazy mode."
metadata:
  argument-hint: "[lite|full|ultra]"
license: MIT
---

# The simplest solution that satisfies the task

Understand the accepted outcome and trace the affected behavior and callers
before choosing a solution. Fix the cause where the relevant paths meet.
Choose the simplest design that satisfies the full accepted scope; prefer
clear code over compressed code.

Look first for an existing implementation, then the standard library, native
platform features and installed dependencies. Add a dependency or abstraction
when the actual requirement justifies owning it. Avoid speculative scaffolding,
unrelated cleanup and frameworks for a one-off task.

Keep required error handling, validation, accessibility, recovery and physical
calibration. Describe a deliberate simplification's material limit when it
affects the outcome. Do not ship a reduced deliverable and require Mathis to
ask again for the rest.

Verify meaningful behavior with the smallest useful check, reusing existing
coverage. Follow [tests with a purpose](../../workflows/development.md#tests-with-a-purpose).

## Optional intensity

Default to `full`. `/ponytail lite|full|ultra` selects how strongly to challenge
unnecessary implementation; `stop ponytail` or `normal mode` restores the
ordinary task defaults.

- **lite:** mention a materially simpler alternative when useful.
- **full:** use the simplest complete solution.
- **ultra:** actively remove speculative work before adding machinery.

Levels apply to coding work in this thread until changed. They do not reduce
explicit requirements, govern non-coding requests, or limit requested reports,
explanations and evidence.
