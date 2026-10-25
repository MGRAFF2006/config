# Development and review

Follow the [root instructions](../AGENTS.md). Read this workflow when implementing, verifying, or reviewing changes.

## Code and proof

Use the [decision workflow](decisions.md) for unresolved alternatives and actions
that are difficult to reverse. Keep trials isolated and reviewable; a PR does
not make production side effects reversible. Record consequential experiments,
including failed options and their evidence, in the relevant issue or PR.

Match the repo's stack, structure, types, formatter and focused checks. Prefer
existing utilities and the standard library; avoid dependencies and frameworks
introduced for speculative needs. For new TS apps prefer modern Vite tooling
unless project context says otherwise; use Bash/TypeScript for glue and Compose
for existing multi-service patterns. Bash scripts use `set -euo pipefail`.

Do not weaken types, silently catch errors, add placeholder abstractions or
drive-by refactors. Comment non-obvious intent, not what the code already says.
New projects need a useful README and .gitignore; use relative/configured paths
in shared code.

Run the smallest meaningful verification; repo-required checks win. Do not run
whole-repo suites casually. For visible changes, exercise the changed flow in
the real app and show the outcome, including clipping/empty/error states when
relevant. Name the exact unverified target or missing capability.

Reuse the existing skill for a capability and project record for decisions.
Use GitHub issues and PRs for work and review history, and releases and changelogs
for shipped progress, rather than parallel agent notes. Shared skills live in
`agent/skills`; install links with
`scripts/install-agent-kit.sh`. Descriptions select workflows; load only what
the task needs. Review upstream skill changes instead of blindly replacing
personal adaptations.

## Tests with a purpose

Give each test a clear scope: a required behavior, contract, invariant, or
concrete regression. Be able to explain the scenario, expected result, and real
failure it would catch. Derive expectations from the requirement, not by copying
the implementation's algorithm or conditions into the test.

Do not add tautological assertions, arbitrary constant checks, or tests whose
only purpose is confirming that an `if`, loop, language feature, or library works.
Test the application rule expressed by that code. Even a one-line permission
check can deserve meaningful coverage; syntax and line count do not determine
test value. Source-text assertions need a reason that the representation itself
is part of the contract.

Exercise the actual production behavior at the narrowest useful boundary: unit,
integration, or end-to-end, depending on the failure being caught. Mock external
boundaries when needed, but do not replace the behavior under test and then
assert the mock's predetermined answer. Include important error and boundary
cases within the test's stated scope, rather than generating speculative cases
or chasing test counts and coverage percentages.

Check that the assertion would detect a plausible break in the intended behavior.
For regression fixes, demonstrate failure before the fix and success afterward
when practical; the failure must be the relevant defect, not a broken fixture or
import. State when the earlier failure was not reproduced. Reuse or extend
existing tests when they already cover the concern. Do not add tests for
reversible, low-impact edits merely as ceremony; repository-required checks
still apply. Reviewers should assess what tests prove and miss, not just whether
they pass.

## GitHub work and review history

Git permissions and merge conditions live in the root. Research within an
implementation task can support its authorized changes.

Use GitHub as the durable record of substantive work. Give independent
implementation work its own branch and worktree. Keep changes small and
reviewable, link related PRs and their dependencies, and record reviews and
their resolution on the relevant PR. Commit messages explain changes; PR
descriptions explain the problem, decisions, resulting behavior, and verification.

Match the GitHub structure to deliverable changes. A coordinating agent or
research task does not automatically need its own branch or PR. Preserve
consequential findings and decisions in the relevant issue or PR so someone can
reconstruct the work without reading agent conversations.

## PR names, descriptions, and evidence

Use [reviewable-pr](../skills/reviewable-pr/SKILL.md) when preparing or updating
PR titles, descriptions and evidence. Follow repository naming conventions and
templates; otherwise use a short name describing the concrete behavior. Keep
validation tied to the target and revision, and performance claims tied to
actual measurements and conditions. Publish concise evidence accessible to
reviewers, with secrets and private transcripts excluded.

## Agent attribution

Agents currently share Mathis's GitHub account; separate accounts may come later.
Keep agent attribution explicit regardless of the posting account. Append a
Markdown blockquote to agent-authored issue and PR descriptions, comments,
review submissions, and individual inline review comments:

> **Agent:** `<stable-agent-id>` · **Role:** `<role>`
> **Runtime:** `<app/harness/provider>` · **Model:** `<actual-model-id>` · **Reasoning:** `<actual-effort>`
> **Context:** `<actual-thread/task-id>` · **Revision:** `<full-reviewed-SHA, for reviews>`

Use the same agent identifier throughout its assignment and include enough task
or thread context to distinguish it from agents in other work trees. Roles can
include author, manager, feature reviewer, or bug reviewer. Read model and
reasoning level from the executing runtime when exposed; an available-model
catalog or configured default is not proof of the model executing this work.
Record changes in model or effort on subsequent posts without changing the
agent's identity. Use `unknown` for metadata that is not exposed; use
`not applicable` only when that is established. Do not guess identifiers or
invent thread links. Include the exact reviewed revision for review findings
and recommendations; omit that field when the post is not a review.

When posting another agent's findings, distinguish the posting agent from the
review author and preserve the review author's attribution and reviewed commit.
Do not present a relayed review as your own independent work. An attribution
block records provenance; it does not create a separate GitHub identity or
replace genuine independent review or required GitHub approvals.

In agent-authored commit bodies, include an `Agent: <stable-agent-id>` trailer
matching the owning PR's attribution. Preserve Mathis's configured Git identity;
do not change Git configuration or invent author identities. Attribution does
not grant permission to post, commit, or disclose private transcripts.

## PR scope and dependencies

Give each PR one coherent, stated outcome and acceptance criteria. Keep its
scope reasonable for a reviewer to understand the change, dependencies, and
verification. Judge this by concerns and behavior, not an arbitrary line count.
Split work that needs separate reasoning, rollout, or acceptance into separate
PRs. Include the implementation, tests, and documentation needed for the stated
outcome; avoid unrelated cleanup and speculative features.

Keep that boundary stable through review rounds. Review feedback does not
authorize new features or a broader redesign. Fix defects in the scoped change;
put additional concerns in separate linked PRs within the authorized task, or
record them for a later decision when they exceed that authorization. Do not
treat every suggestion as a new acceptance requirement.

When another change is a prerequisite, make it a lower PR in the stack and base
the dependent PR on it. When follow-up work depends on the current change, stack
it above. State the relationship, base, and merge order in each PR. Independent
concerns need linked separate PRs without an invented dependency. Verify each
layer against its declared base and the combined affected flow. After a base or
HEAD changes, refresh the relevant checks and final review for the actual result
being merged.

Scope separation must not defer a correctness or safety requirement past the
merge that needs it. An introduced regression belongs to fixing the current
outcome; a prerequisite fix in another PR must land before its dependent change.
Optional improvements and unrelated existing bugs do not expand or block the
current PR unless they affect its correctness or safety.

## Branch maintenance

Classify branches by their role and dependencies, not just their names. Never
force-push shared or higher-level branches, including default, release,
integration, and any branch used as a base by another PR, agent, or task. Owning
a branch does not permit rewriting it once other work depends on it. Update
these branches through the authorized PR and merge workflow.

You may rebase or otherwise maintain an isolated task branch you own when no
other work depends on its history. Preserve its starting tip in a recoverable
Git reference, inspect local and actual remote changes, and confirm ownership
and dependencies first. A shared GitHub account does not establish that another
agent's commits belong to you. Preserve unrelated working-tree changes.

If publishing a rewritten owned task branch, use an explicit branch target and
`--force-with-lease=<ref>:<expected-oid>` against the remote tip you inspected.
Do not use plain `--force` or force-update multiple branches. A rejected lease
means re-inspect and reconcile the changed remote, not weaken the protection.
The prohibition on force-pushing higher-level branches still applies with a lease.

When maintaining a stack would require rewriting a base other work uses, use
merge-based updates or a new task branch and adjust PR dependencies while
preserving existing history. Do not rewrite the base merely to simplify the
stack. Refresh checks and final reviews after the changes as required above.
Hard resets and history rewrites outside the owned isolated-branch boundary
retain the root's explicit-authorization requirement.

## Independent review and merge evidence

Give independent reviewers the intended outcome and constraints, but require
them to inspect the implementation and affected callers or shared behavior.
Review both acceptance criteria and bugs or oversights beyond the feature's
happy path: regressions, missing cases, error handling, and effects on existing
behavior. Check security, data integrity, concurrency, and lifecycle assumptions
where relevant. A review that only confirms the feature description is incomplete.

Make findings actionable: identify the affected location, triggering conditions,
expected and actual behavior, and consequence. Support them with the most useful
evidence available: an exact error excerpt, failing test or minimal reproduction,
annotated screenshot, recording, or diagram. Use inline comments and small code
suggestions where appropriate. Keep the explanation understandable without relying
on an image alone, distinguish reproduced failures from inferred risks, and apply
the PR evidence guidance above. Review evidence should clarify the finding without
expanding the PR's scope.

For substantial changes, add a distinct independent review focused on bugs and
oversights alongside the review of intended behavior. For a small change, one
independent reviewer can explicitly cover both perspectives; do not create a
fixed reviewer hierarchy. A reviewer must not be the author of the changes they
approve, even when another agent in the same work tree performs the review.

Record the exact reviewed commit, scope examined, concrete findings, verification
performed, remaining gaps, and an explicit merge recommendation on the PR.
Use evidence rather than numerical confidence as the merge gate. Classify
findings by their effect on the scoped change: correctness or safety blockers,
additional work for separate PRs, and optional suggestions. Respond with a fix,
evidence explaining why a finding does not apply, or the linked additional PR
and its dependency. A separate PR does not resolve a blocker until the required
fix is integrated. Required checks and actionable correctness or safety findings
must be resolved before merge; unknown or missing check results are not passes.

A changed HEAD needs fresh final review. Before merging, inspect automatic
deployments, migrations, and other external effects; apply the root permissions
and the [decision workflow](decisions.md). Approval of a code change does not
silently authorize effects outside the task's scope.
