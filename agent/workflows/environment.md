# Machines, systems, and GUI work

Follow the [root instructions](../AGENTS.md). Read this workflow when choosing a host, changing a system, or using a native GUI.

## Targets, machines and files

The agent kit is `~/Documents/config/agent/`. Its
[fleet index](../fleet/README.md) and machine records hold host facts and procedures.
Identify the current machine with Tailscale, not only hostname, and verify
reachability. Choose the role and package manager from the target's record and
follow the project's runtime. Do not assume a host is online or an old recorded
service is healthy.

When targets differ, state the account, host, repository/worktree and environment
before acting. Resolve ambiguity that changes the outcome: a local CMS change
does not update production. Use existing SSH aliases and Tailscale paths.
Do not invent connection endpoints or expose Sunshine publicly.

Keep durable system/shell/editor/package/symlink changes in
`~/Documents/config`, using its setup/install flow and package lists. Code
normally lives in `~/Projects`; documents under `~/Documents`. Use Git for
durable work. Do not overwrite project instructions, scatter untracked config
around home, or create a second notes/dotfiles layout.

For long shell jobs use named tmux on the target host; report the name and
completion/failure. Local tmux cannot keep a sleeping laptop running. Before
disk-heavy work, check free space, retain at least 10 GiB, and reuse compatible
caches. Avoid broad builds on battery. Do not reboot/shut down a machine or
change power management without an explicit request; avoid disrupting an
active gaming/Sunshine session.

## Handoff to the right computer

When Mathis requests work on another computer, or the current thread is on the
wrong host for the task, prefer a thread running directly on the correct host.
Reuse an existing relevant owner when possible. Create new threads only when
the current request and runtime rules permit it; otherwise use an established
direct SSH path when suitable, or report the routing gap. Do not build a long chain of tunnels, wrappers,
or local replicas merely to keep execution in the originating thread.

Verify the current Tailscale identity, target reachability, and the target's
actual thread-launch service or capability. Use the app's supported native
routing and workspace selection; do not assume a local launch targets another
host. Confirm the destination account, host, repository/worktree, branch, and
environment before execution. If native launch is unavailable, report the exact
gap and use an established direct SSH path when it is suitable and simpler.
This preference does not require a new thread for a single bounded SSH command.

Pass the requested outcome, scope and permissions, acceptance criteria, relevant
decisions, exact paths and branch/revision, completed work and evidence, pending
work, and blockers. Include related PRs and ownership. Note source-only dirty
changes explicitly; do not assume they exist on the destination or copy dirty
trees, authentication state, or raw transcripts as a shortcut.

Retain the returned thread/task identifier, verify that the destination started
in the intended context and accepted ownership, and link it for Mathis. Check
existing launches before retrying an uncertain result. Stop duplicate execution
on the source host after the handoff is confirmed. A simple relocation needs no
permanent extra manager: the destination can own the task directly. In divided
work, preserve the one interaction owner or explicitly hand that responsibility
over so questions and decisions do not split across threads.

## GUI work alongside me

Prefer application APIs and T3's collaborative browser. Native GUI work uses
the laptop's separate agent desktop, documented in its fleet record. A hidden
workspace or virtual monitor in my session still shares focus.

Do not focus my windows, switch workspaces, capture my physical screen, or send
input to my desktop unless I explicitly ask. Launch separate instances in the
agent session, respect profile locks, and never copy credentials to bypass a
running profile. Check screenshot/input targets and fail if that session is
unavailable. Stop only processes you own. Preview audio is opt-in and must stop
when the demo ends.

Permission to test an application authorizes the collaborative browser or an
isolated agent desktop, not control of Mathis's active desktop. If the required
isolation is unavailable, report the missing capability and continue independent
work; do not silently fall back to his session.
