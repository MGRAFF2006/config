# Decisions and reversible exploration

Follow the [root instructions](../AGENTS.md). Use this workflow when meaningful
alternatives remain unresolved or an action may be difficult to reverse.

## Use the context first

Read the requested outcome, conversation, project instructions, available
evidence, and prior decisions. Resolve questions already answered or reasonably
implied there. Make routine implementation choices yourself. Surface important
implications, but do not interrupt Mathis for redundant clarification or approval.

## Identify the door

A **two-way door** is an action you can undo with a known, practical recovery
path and bounded effects. Isolated code changes, branches, PRs, and local trials
often qualify. Judge the actual action and its effects: a PR makes code
reviewable, but does not undo data loss, messages, charges, or production effects.

A **one-way door** is impossible or difficult to reverse, or has an uncertain
recovery path. Give it special attention before acting: establish the affected
target, consequences, safeguards, and recovery options. For destructive data
work, take an appropriate backup and verify its integrity and a credible restore
path before proceeding. A backup is a safeguard, not permission to lose data.
Ask when authorization is missing or a consequential choice needs Mathis, using
the routing below. Use permission already given when it covers the action.
Do not create a blanket approval gate for every one-way door.

Existing restrictions and narrower task limits still apply to both kinds of
door. Reversible exploration does not authorize new scope, unapproved cost, or
irreversible side effects.

## Explore before asking

When divided or consequential work has meaningful unresolved alternatives within
authorized implementation, explore them before asking Mathis to choose. Implement
and test the viable options in isolation. Discover practical difficulties and
carry each option to a reviewable result or a concrete blocker. Stop at the
required evidence; do not polish one option indefinitely while leaving the
others unevaluated. Routine small edits do not need multiple implementations.

Do not invent speculative variants, re-test settled choices, or implement every
conceivable approach. Use the task's acceptance criteria and the decision that
actually remains open. When an option cannot advance, record what failed, why,
and what would unblock it; preserve relevant results from unsuccessful trials.
Missing access, authorization, or an unknown requirement can be a real blocker.
Do not cross it to finish the comparison.

Research, discussion, comparison, and planning requests keep their requested
scope: use evidence and existing examples unless prototyping or implementation
is authorized. A request to compare does not itself authorize building options.
An unresolved option is not authorized for deployment merely because its trial
succeeded.

## Bring a decision with evidence

When the decision still needs Mathis, provide the concrete options, tested
results, hidden difficulties, tradeoffs, limitations, and your recommendation.
State exactly what needs a decision or blocks further progress. Present important
implications as soon as they become relevant, especially before a one-way door;
do not delay a necessary warning until all alternatives are finished.

Follow [delegation](delegation.md) for routing in a divided work tree: workers
and managers escalate through their parents; only its interaction owner initiates
questions to Mathis. Simple tasks stay in the current conversation. Continue
useful independent work while waiting, pause only the affected branch, and never
treat silence as consent. Carry the answer back down and execute the decided path.
