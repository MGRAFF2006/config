---
name: release-readiness
description: "Use when preparing a release, changelog, downloadable binary, signing setup, or app-store package for an existing project."
---

# Release readiness

Read the repo's release workflow, prior release and signing references. Compare
the intended deliverable with what its current artifacts actually contain.
Use releases/changelogs for progress; do not create agent milestone documents.

Run focused required checks, build the intended package using existing tooling,
and exercise the artifact's installation/start path where available. Verify
version, platform/architecture and required data/migrations. Resolve signing
material through the secret store and test recovery without printing keys.

Follow the requested commit/push/PR/publish scope and exact-HEAD review rules.
Merging a PR is not evidence that a release exists: verify the published artifact
when publication was requested. Name unverified platforms and manual store steps.
