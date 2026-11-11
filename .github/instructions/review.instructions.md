---
description: "Use when reviewing code, tests, architecture, security-sensitive changes, agent-built work, or an integration diff."
---
# Review

- Review the actual diff against its base and the stated acceptance criteria, then inspect enough surrounding code and tests to validate behavior. Prioritize correctness, security, regressions, reliability and missing coverage over style.
- Check relevant NetPulse invariants: loopback authentication and Origin/Host handling, consent and rate limits, privacy, monotonic timing, SQLite transaction and restart behavior, bounded queues and cleanup, API/CSV precision, and degraded-mode behavior.
- Report only actionable issues with severity, file and line, a concrete failure scenario and recommended correction. Separate verified defects from questions and clearly state assumptions.
- Review tests for whether they exercise the required behavior and thresholds. Report commands executed, limitations and residual risks; do not claim tests passed without evidence.
- A reviewer should not modify the candidate while reviewing. The coordinator or builder resolves findings, and the reviewer verifies material fixes.
