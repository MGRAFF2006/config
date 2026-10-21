# Prepare a computer for AI work

Use this when adding a computer, replacing one, or checking whether an existing
one is ready. Keep the same config repo and machine records. This procedure
does not require a new fleet-management service.

## Existing laptop

The core tools are already installed. From the config checkout, run:

```bash
bash scripts/install-agent-kit.sh --dry-run
bash scripts/install-agent-kit.sh
bash scripts/install-agent-kit.sh --check
```

Restart the agent, open `agent/fleet`, and ask it to report which instructions
and skills it can see. In Codex, `/skills` lists available skills; try
`$machines` for a machine task. Check the app's actual harness instead of
assuming every interface loads the same files.

The installer preserves replaced files in its printed backup directory. For
rollback, restore only the affected paths from that directory: remove the new
symlink with `unlink`, then move the original back. If there was no original
file, removing the kit's symlink is enough. A backed-up skills directory may
contain unique local skills; review it before importing anything into the shared
kit. Restore retired rule or skill links from the backup if rolling back.

## New Arch computer

1. Install Git and the existing transport tools. Use the repo's package lists
   for a complete machine setup; for AI readiness alone, the following is a
   focused starting point:

   ```bash
   sudo pacman -S --needed git github-cli openssh rsync tmux ripgrep tailscale syncthing openai-codex
   sudo systemctl enable --now tailscaled.service
   sudo tailscale up
   ```

   Follow the normal Tailscale login flow. Choose the device's real name and
   permissions; do not reuse `laptop` or `desktop` for another computer. Confirm
   current package availability with `pacman -Si` before installing if needed.
   The baseline package lists already include most tools; `openai-codex` is the
   package for Codex, whose executable is `codex`.

2. Get `~/Documents/config` through the existing Syncthing share or clone
   `MGRAFF2006/config` with your established GitHub access. Use one checkout as
   the source of truth; do not pull Git changes concurrently with Syncthing
   rewriting that checkout. Syncthing service/configuration is device-local.
   Enable its user service when ready:

   ```bash
   systemctl --user enable --now syncthing.service
   ```

   Configure the folder/device pairing in Syncthing. If you also sync the whole
   Documents folder, follow the config repo README's nested-folder exclusions.
   Do not sync `~/.codex`, `~/.cursor`, `~/.config/opencode`, `~/.ssh`, or provider
   auth/state directories. The kit syncs source files and recreates local links.

3. Run the focused kit installer and `--check`. It works independently of the
   device name. The full `scripts/link-home.sh laptop|desktop` is intended for
   those existing dotfile profiles; do not pass an invented profile to it for
   a new device. Adapt the broader dotfile installer separately when needed.

4. Install only the AI interfaces you plan to use. T3 Code is already in
   `packages/aur-common.txt`; OpenCode is in `packages/common.txt`.
   Codex CLI alone is enough to start. Login through each tool's own flow;
   `codex login` is the normal Codex entry point. Do not copy another device's
   `auth.json`, session database, or private SSH keys.

5. Configure remote access only if this computer should host work. Generate
   its own SSH key locally if needed, enroll the public key through your usual
   authorized process, and verify the host key. Prefer the existing OpenSSH
   pattern over changing the whole fleet to a different SSH mechanism. Keep
   durable SSH aliases in the config repo's established config flow; do not
   silently overwrite a machine's current SSH config or expose ports publicly.

6. Copy [the machine template](machines/TEMPLATE.md), fill it from live checks,
   and add the record to [the Fleet index](README.md). Record any missing login
   or unavailable remote steps. Verify one small real task in a new agent
   session and inspect the resulting files/diff.

The tool paths above are supported by [Codex's instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [Tailscale's setup guide](https://tailscale.com/docs/how-to/quickstart).
Arch package availability should be checked on the target machine; do not use
Debian commands from a third-party fleet installer.

## Other operating systems

Use the same Markdown context and shared skill format. Install Git, SSH, tmux
where supported, and the chosen harness with that OS's official instructions.
This shell installer targets Linux-style paths; macOS may work with its normal
Unix tools, but is untested. Native Windows needs its own linking/installation
flow; do not assume this script supports it. Keep OS-specific facts in the new
machine record rather than rewriting the Arch defaults for every computer.

## Validate remote work

For the existing desktop, first run a bounded read-only probe:

```bash
tailscale status
ssh -o BatchMode=yes -o ConnectTimeout=5 desktop 'uname -s; command -v tmux; command -v codex'
```

If that fails, report the host as unavailable and continue appropriate local
work. When it works, run long jobs in a named tmux session **on the target host**.
For example, an explicitly requested project build can be started after checking
the project's instructions and working tree:

```bash
ssh desktop
cd ~/Documents/your-project
tmux new -s project-build
# Run the project's documented command; detach with Ctrl-b, then d.
```

Reconnect with `ssh -t desktop 'tmux attach -t project-build'`. Supply the real
project path and command; the example path is a placeholder, not a known repo.
tmux preserves terminal sessions across disconnects, as documented in
[tmux's guide](https://github.com/tmux/tmux/wiki/Getting-Started). It cannot make
a suspended or powered-off computer execute work.

## Useful live checks

```bash
tailscale status --json
lscpu
free -h
command -v codex opencode t3code tmux
codex --version
opencode --version
systemctl --user is-active syncthing.service
git -C ~/Documents/config status --short
```

Only save the fields needed for the record. Do not dump whole authentication
files, environment variables, or Syncthing configuration into a transcript.
