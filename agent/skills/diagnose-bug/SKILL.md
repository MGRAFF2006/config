---
name: diagnose-bug
description: "Use for difficult bugs, recurring failed fixes, regressions, or measured performance problems that need a reliable reproduction."
---

# Make the failure observable

Get one small command or real-app sequence that demonstrates the reported
failure. Record the actual error and relevant host/version. If reproduction
is unavailable, say so and distinguish hypotheses from confirmed causes.

Trace the shared code path and callers. Rank plausible causes, instrument the
boundary, and change one hypothesis at a time. After repeated fixes fail the
same check, test their common premise instead of repeating the patch.

Fix the root cause with the smallest relevant regression check. Exercise the
reported path again and remove temporary instrumentation. For performance,
keep comparable before/after measurements and the command that produced them.
Use the repository's focused checks, not an unsolicited whole-repo suite.
