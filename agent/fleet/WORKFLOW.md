# Working with AI across your projects and computers

The useful habit is to give the agent a clear outcome, let it inspect the right
context, and steer it toward a result you can verify. Fleet supplies computer
context; each project supplies its own code and conventions. You do not need
an elaborate ticket pipeline for every task.

## Choose the workspace

| Task | Open |
| --- | --- |
| Fix or build an application | That application's repo |
| Prepare a machine, choose a host, tune your AI setup | `~/Documents/config/agent/fleet` |
| Change shell, desktop, or package configuration | `~/Documents/config` |
| Research or write project documentation | The project or existing docs repo |

T3 Code can remain your main interface. Codex is a harness it can launch;
OpenCode is another option you already have. Choose the tool that
works for the task and check its actual executable/version when debugging.
Avoid changing models or adding integrations just because another developer
uses them. Tool capabilities are separate from reusable Markdown instructions.
The [T3 Code repository](https://github.com/pingdotgg/t3code) documents the app.

## Start a fresh task

Use one thread per coherent outcome. Give the agent the problem and the
important limits, then let it inspect manifests, project instructions, and
existing implementations. For example:

> The JCH scoreboard loses its selected match after refresh. Find the cause,
> fix it using the existing stack, and show me how you verified the behavior.

> I want to compare two approaches for this feature. Research them and save a
> concise note with sources and a recommendation in this project's docs. Do
> not implement the feature yet.

> Prepare this new computer for my AI workflow using the existing config repo.
> Inspect what is already installed, set up the kit, and document the machine.

For an unclear or large task, discuss the outcome first. Ask the agent to
challenge assumptions or interview you about the few decisions that matter.
Once the shape is agreed, implement a useful slice. Save a plan only when it
will help the next session resume; small fixes need no additional plan file.

This conversational approach, short prompts, and fresh task threads appear in
Theo's [May workflow video](https://rosetta.to/u/t3dotgg/how-i-code-with-ai-changed-a-lot).
These examples are adapted for your projects, not copies of his private prompts.

## Steer during the task

Read the agent's findings and correct wrong assumptions early. A screenshot
with a marked problem can be more useful than a long description. Provide
the relevant local checkout when an existing implementation should serve as
a reference. On Linux, use your current desktop's screenshot and dictation
tools; Theo's macOS utilities are not required.

Voice dictation is optional: dictate the desired outcome into the prompt box,
check paths and technical names, then submit. This kit installs no recorder or
speech service. Theo's [voice workflow demonstration](https://www.youtube.com/watch?v=NvVbCqDgfCs)
shows why machine context helps even when operating away from a keyboard;
[an unofficial transcript](https://moderncreator.app/2026-09-16-theo-t3-gg-how-i-code-without-typing)
is available for reference.

When a long session becomes confused, begin a fresh thread with a brief handoff:
objective, relevant files/branch, completed work, remaining work, and proof so
far. Preserve the code and useful notes; avoid copying the whole conversation.

## Ask for evidence

For code, inspect the diff and the smallest relevant check. For a UI change,
prefer a real run, screenshot, or browser demonstration when the tool can do
it. For a system change, verify the resulting command/service/link rather
than accepting “configured” as proof. For research, require sources and a
clear separation between facts, unknowns, and proposed choices.

Your established rules still apply: no commits, pushes, PRs, merges, destructive
changes, or remote power actions beyond what you authorize. A more autonomous
workflow does not require adopting Theo's personal merge permissions. Share
artifacts externally only when requested; a local screenshot or recording is
enough for ordinary verification.

## Use skills when they help

| Skill | Useful request |
| --- | --- |
| `ponytail` | Keep coding changes small and reuse existing solutions |
| `machines` | Choose a host, diagnose remote access, or manage synced config |
| `onboard-machine` | Prepare or verify an additional computer |
| `research-notes` | Investigate a topic and save sourced documentation |
| `write-agents-md` | Create focused project instructions or edit your letter |
| `prune-agent-context` | Investigate conflicting or stale agent guidance |
| `audit-agent-failures` | Learn from specific repeated failures you provide |

In Codex, mention a skill with `$name` or inspect `/skills`. Other tools have
their own skill selectors. A skill is instructions and optional resources;
it cannot give an agent a browser, account access, or a connector it lacks.
Keep new integrations tied to a real task. Your ponytail skill now lives in
the shared kit; built-in Codex skills remain managed by Codex.

## Work that continues after lid close

Your recent hung thread demonstrates the practical boundary: a laptop-hosted
app or job may stop responding when the laptop suspends. tmux helps with
terminal disconnects, not sleep. The desktop must be online and awake to host
work that continues while the laptop is closed.

When remote hosting becomes available, verify one small job there first. Keep
builds/servers in named remote tmux sessions, then connect your interface using
its supported remote workflow. Persistent GUI agent threads depend on that
app's server and reconnection behavior; running an unrelated tmux session does
not move a GUI thread to another machine automatically.

After an interruption, use:

> Resume this task from the existing files. Check the working tree and running
> processes first, identify what completed, and continue the unfinished steps.

## Improve the setup from experience

After a repeated problem, give the agent the relevant failure examples and
ask for the smallest fix. Prefer clearer code or a reliable command over a
permanent new instruction. If a note is needed, put it in the layer it belongs
to: your letter for collaboration preferences, the machine record for host
facts, project `AGENTS.md` for project gotchas, and a skill for a recurring task.

Review stale guidance after significant tool or model changes. OpenAI's
[guidance on instruction scope](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
also recommends keeping reusable instructions focused and avoiding mandatory
doc-reading routines for unrelated tasks. Preserve your explicit preferences
unless you choose to change them.
