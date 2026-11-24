# Delegation

Follow the [root instructions](../AGENTS.md). Read this workflow when delegating or coordinating work.

Own the outcome you receive until it is complete. Understand the problem, its
boundaries, and what evidence would demonstrate success. Delegation is authorized
within the requested scope, including research and comparison tasks; children
inherit the same limits and responsibility for their assigned outcomes.

## Interaction and decision routing

Handle simple tasks directly in the current user-facing thread. For substantial
work divided among agents, designate one interaction owner for the whole tree,
normally the existing conversation with Mathis. Keep it responsive and delegate
task management and execution below it. This is a division of responsibilities,
not a fixed hierarchy: use only the managers and workers the problem needs.
Children do not each create an interaction thread. Do not create new top-level
conversations unless Mathis requests them.

Only the interaction owner initiates questions to Mathis or uses user-input tools.
Managers and workers send unresolved decisions to their parent, which resolves
them within scope or passes them upward. Apply the [decision workflow](decisions.md)
before escalating: include the question, relevant evidence, attempted options,
tradeoffs, recommendation, and the exact blocked action or missing authorization.
Report urgent implications promptly rather than waiting for every investigation.

Continue independent work while a decision is pending. Stop only the affected
branch at its actual blocker or authorization boundary; silence is not consent.
The interaction thread returns Mathis's decision through the parents, who update
the affected assignments and acceptance criteria. Keep operational coordination
between agents; give Mathis meaningful progress, decisions, and results. Make
delegated work inspectable through named owners, assignments, results, and
relevant PRs. Mathis can inspect or steer any delegated task; relay consequential
decisions through the tree so affected agents share the same understanding.

## Decompose and deliver

Delegate problems and questions with context, constraints, relevant evidence,
and acceptance criteria. Give the receiving agent freedom to investigate and
choose its approach. Distinguish established facts from your hypotheses.

Include the child's stable agent identifier, role, and actual task/thread
context in its assignment. It must preserve that identity in deliveries and
follow the [attribution format](development.md#agent-attribution) when posting
to GitHub. Relay another agent's review with its original authorship intact.

Delegate one conceptual layer deeper at a time. Identify the immediate
subproblems; let their owners decide how those break down further. Investigate
enough to make a meaningful decomposition. Do not pass the same vague assignment
down unchanged.

When you can identify a direct, justified fix and verify that it solves your
assigned problem, implement it. Otherwise, delegate the unresolved subproblem
or investigation. Grow the tree where the problem needs it: multiple children
for independent angles, components, research questions, or reviews; dependent
work follows its prerequisites. There is no prescribed depth or agent count.

Research and comparison are valid work anywhere in the tree and can themselves
be decomposed. Give investigations a question and an expected result: evidence,
alternatives, a recommendation, and remaining uncertainty.

As a parent, maintain the overview, coordinate boundaries and dependencies,
resolve conflicting findings, and integrate results. Give each child a clear
scope and ownership of its files or deliverables; avoid competing coordinators
and concurrent edits to the same files. Check deliveries against your acceptance
criteria and verify the combined outcome. A child's completion report is input
to your judgment; you remain accountable until your outcome is complete.

## Choose providers and models

Resolve available providers and models from the running harness (in T3,
`orchestrator_capabilities`); do not hardcode model IDs. Children use the
parent's provider and model unless the assignment gives a reason to change:

| Work | Default |
| --- | --- |
| Interactive work, implementation, coordination | The parent's model; at the top, Mathis's default (Claude flagship) |
| Narrow searches, summaries, mechanical edits | A smaller model or lower effort from the same provider |
| Independent or second-opinion review | A fresh agent; for substantial or risky changes, the other cloud model family (Claude or GPT) |
| Small private or offline tasks with a short context | Laptop NPU |

Mathis's explicit choice overrides this table. Size effort to the task: higher
reasoning for design, security and final review, lower for routine work.
Laptop NPU agents run only while the laptop is awake and have a 32K context;
give them self-contained inputs and verify their output locally. Do not send
material Mathis kept local to a cloud model without Mathis's permission; PR review
rules still apply to anything that becomes a PR. A usage limit or unavailable
provider blocks that branch: report it through the tree rather than
substituting a model.
