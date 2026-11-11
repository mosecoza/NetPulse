---
description: "Use when planning, writing, running, or reviewing automated tests, acceptance gates, and regression coverage."
applyTo: "tests/**/*.py"
---
# Testing

- Use the existing `unittest` runner unless a new test dependency is justified by the task. Run `python -m unittest discover -s tests -v` from the project root; use targeted selectors while iterating and run broader tests for integration changes.
- Assert observable results and the exact contract, not implementation details or only a happy path. Cover invalid inputs, error paths, timing boundaries, concurrency, cleanup and security properties when relevant.
- Keep tests deterministic and independent: use temporary directories and databases, injected clocks, fake probes, controlled subprocesses and local mock services. Do not depend on administrator privileges, live targets, real user data, wall-clock sleeps or network availability by default.
- Validate platform-specific behavior on supported platforms where possible; distinguish simulation from actual Windows, macOS or Linux execution. State platform and tooling limitations explicitly.
- Associate tests with a builder's owned files; the coordinator owns shared integration tests. Never declare a phase gate passed without exercising its specified measurable criteria.
