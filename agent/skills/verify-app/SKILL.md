---
name: verify-app
description: "Use when verifying a user-visible UI, CLI, service, simulator flow, or a claimed behavior change in a running application."
---

# Prove the requested behavior

Read the repo's existing launch and verification commands. Prefer its harness;
do not invent another browser or test stack. Follow the current runtime's
browser authorization and tooling rules. Native GUI work belongs in the separate
agent desktop.

Confirm the actual instance, version, account, environment, fixtures and owned
port before driving it. Exercise the actual launcher or client route, then the
changed flow and its saved/reopened data. Name any environment mismatch that
remains untested. Capture concise evidence
that survives cleanup. Test small screens and empty/error states when relevant.

Stop only processes/media created for this verification. Keep preview audio
opt-in. Do not call a stand-in or a build a real-target verification; name what
it proved and what remains unverified. A reusable project recipe earns its
place after its launch/drive/evidence/cleanup steps have run successfully once.
