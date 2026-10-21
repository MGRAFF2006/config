# Working in Mathis's Fleet

This workspace manages machine context, shared skills, and AI workflow notes.
Start with `README.md` and the relevant `machines/<name>.md` when a task concerns
a computer. `../GLOBAL.md` holds Mathis's personal defaults and collaboration
preferences, shared by all local tools.

Keep durable changes in the enclosing config repo. Verify the current Tailscale
identity and remote reachability before choosing where to run something. A
machine record describes capabilities, not its current online state.

Use the focused `../../scripts/install-agent-kit.sh` for agent setup; the full
`link-home.sh` also changes shell, editor, and desktop links. Keep authentication,
chat databases, and raw transcripts out of this workspace. Update a machine
record after a verified change and distinguish observed facts from user reports.

Do not commit or push unless asked. Do not change power management just to keep
an agent running. For durable jobs, use an awake host and tmux on that host.
