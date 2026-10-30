# Boat cloud sandboxes

Use Boat for disposable isolated development work or extra compute. Existing
Fleet hosts remain available; choose the environment that fits the task.

## Setup

From `~/Documents/config`:

```bash
bash scripts/install-boat.sh
~/.local/bin/boat login
~/.local/bin/boat status
~/.local/bin/boat limits
```

The focused installer fetches the official production CLI into `~/.local/bin`,
which the existing headless shell setup already puts on PATH. It does not edit
shell files. Each host needs its own login; use the GitHub identity already
connected to Mathis's Boat account. A GitHub CLI login is separate from Boat's
device login. Authentication lives in `~/.config/ascii/boat/`, outside this repo;
never sync or copy it into a sandbox or Git.

For an agent without an interactive terminal, `boat login --json` prints a
browser link and device code. Complete that sign-in, then run
`boat login --wait --json` to save the session. Do not save the pending login
response in documentation. API keys can instead be supplied through
`boat login --key-stdin` using a private secret source.

## Use

- Stay within the existing plan. Choose the smallest suitable runner and keep
  CI fan-out limited. Run PR checks and default-branch push checks without
  duplicate feature-branch push runs. Cancel superseded jobs; rerun only checks
  affected by a fix or an evidenced transient failure. At a start or compute
  quota limit, defer work; do not repeatedly retry, add wallet funds, enable
  auto top-up or change the subscription without Mathis's explicit request.
- Check `boat status`, `boat limits` and `boat list --all` before starting work.
  Prices, billing scope and available compute come from the live account.
- Use explicit sandbox IDs; shell-local `current` is unsuitable for agents.
- For a short isolated check: `boat new --type small --ttl 600 --no-env --json`.
  The JSONL `ready` event contains `id`. `--no-env` withholds account credentials
  and repository injection; use it for untrusted code and smoke checks.
- Run commands with `boat exec <id> -- <command>`. Use `--timeout 0` for a long
  foreground command, or `--detach` for a server and `--status <pid>` to inspect it.
- Clone only the task's repository, or copy the necessary files with `boat push`.
  Confirm access in the sandbox; a connected GitHub account alone does not prove
  clone/push works. Never upload the host's authentication files or vault state.
- Keep automatic stop enabled. `boat stop <id>` ends processes and retains the
  disk for 14 days under the current documented policy. Push commits or copy
  artifacts out before stopping; use `boat delete` only for disposable data.
- `boat prompt` needs a separately configured AI provider; a GitHub connection
  alone does not configure a model subscription or API key.

## Verified state

2026-10-30, `homelab-dev`:

- Boat CLI 1.0.85 installed at `~/.local/bin/boat` and available to noninteractive
  Zsh commands. Device sign-in succeeded; the existing Standard plan is active.
- Sandbox `bx_f9u2fz8c` (`setup-smoke-2026-10-30`, small, 600-second auto-stop)
  passed API command execution, SSH, GitHub API authentication as `MGRAFF2006`,
  `git ls-remote` against `MGRAFF2006/config`, and `docker run --rm hello-world`.
  Git push was not exercised.
- The default `base` environment forwards the linked GitHub account and has no
  repositories selected for automatic cloning. No repository selection was
  changed. The default AI credential profile has no providers connected;
  `boat prompt` is not configured. Agents on the host can use `boat exec` now.
- The CLI generated this host's own `~/.ssh/ascii_box_ed25519` key. Its private
  key and Boat config are mode 0600; no credentials entered this repository.
- Smoke sandbox stopped successfully and its snapshot is available. No sandboxes
  remain running. No plan or payment changes were made.

## Official references

- [Agent setup](https://docs.boat.dev/ai-tools.md)
- [Documentation index](https://docs.boat.dev/llms.txt)
- [CLI reference](https://docs.boat.dev/cli-reference.md)
- [Account access](https://docs.boat.dev/account.md)
- [Pricing and retention](https://docs.boat.dev/pricing.md)
