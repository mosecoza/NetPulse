---
description: "Use when developing or reviewing Python 3.11+ backend, FastAPI, asynchronous jobs, probes, or Python tests."
applyTo: "**/*.py"
---
# Python and backend

- Follow existing Python naming, imports and formatting; add precise type annotations to public interfaces and complex boundaries. Use standard-library facilities and existing dependencies before adding packages.
- Keep HTTP transport separate from domain and storage logic. Validate untrusted input at boundaries, use explicit enums and units, and return documented error envelopes rather than masking failures.
- Use non-blocking I/O in async paths; bound queues, timeouts, concurrency and subprocess lifetimes. Handle cancellation with cleanup and do not swallow `CancelledError`. Avoid blocking the probe loop with disk or network operations.
- Use UTC for persisted timestamps and monotonic clocks for elapsed time; follow the clock, precision and shutdown contracts in `SPEC.md`. Never serialize fabricated or negative duration values.
- Keep credentials and session tokens out of logs, URLs and exception messages. Do not elevate the daemon or bypass consent, authorization, localhost or rate-limit controls.
- Add tests for success, failure, cancellation and relevant boundaries. Follow the testing instructions for the runner, isolation and gates.
