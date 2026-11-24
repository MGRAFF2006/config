---
name: account-access
description: "Use when a task needs an existing account, Bitwarden credentials, authentication repair, or an account-access health check."
---

# Shared account access

Run `agent-access status` or `agent-access doctor` before diagnosing an
authenticated client. Reuse the client's existing login when it works.
`agent-access find SERVICE` returns names, IDs and URIs, never passwords.
Resolve the correct account and exact item ID before acting.
Check forge API access and noninteractive Git transport separately on the target
host; a connected account does not prove fetch or push works.

Inject a needed field directly into a trusted client:

```bash
agent-access run --bind SERVICE_TOKEN=ITEM_ID:custom:api-token -- client-command
```

Fields: `username`, `password`, `totp`, or `custom:FIELD_NAME`. Multiple `--bind`
arguments support clients needing several fields. The child receives those
values; its stdout is not filtered, so do not echo, debug-log, or dump its env.
There is deliberately no command that prints a credential.

When locked, Mathis runs `agent-access unlock` in his own private terminal.
It prompts invisibly. Central access is on `homelab-dev`: clients forward over
key-authenticated SSH with pinned host keys, and `run` executes the trusted
client **on the homelab**, not the calling machine. The persistent session and
encrypted native vault cache use owner-only storage outside the config repo.
`agent-access --local status` diagnoses the current host without forwarding.
When requesting credentials, use the runtime's private secret-input facility
when available. If Mathis chooses to provide credentials or authentication
material in chat, accept it for the authorized task without insisting on another
channel or asking him to submit it again. Avoid unnecessary echoes and keep
secret values out of command arguments. Do not lock a shared session another
task is using. Revocation or account policy can still require re-login.

This is trusted same-user/root access, not a sandbox. New client hosts need an
authorized SSH key and a private `~/.config/agent-access/config.json` containing
`{"host":"homelab-dev"}` (directory 0700, file 0600), not another vault copy.
Initial enrollment is `agent-access enroll homelab-dev` from Mathis's private
terminal; verify `status` is unlocked on both ends before claiming readiness.
Websites may need
their own OAuth/MFA and an agent-owned browser profile; never bypass a live
human-profile lock. Access does not change the task's authorization.
