# NetPulse project instructions

- Treat [SPEC.md](../SPEC.md) as the requirements baseline and [README.md](../README.md) as the current implementation and setup guide. The project is a skeleton; do not claim a planned feature is implemented.
- Keep changes within the requested scope. Read existing code and relevant scoped instructions before editing; preserve unrelated changes and update directly affected documentation.
- Use Python 3.11+ and the existing FastAPI, SQLite, HTML, CSS and JavaScript architecture. Do not introduce a framework, runtime dependency or tooling unless the task requires it.
- Protect localhost interfaces and user data. Do not expose a server before the required authentication, Host/Origin checks and loopback binding exist; do not log session tokens or sensitive network identifiers.
- Add focused tests for behavior changes and run the smallest relevant existing tests, followed by wider checks when integration requires them. Report failures, skipped checks and unverified assumptions.
- For delegated, parallel or review work, follow [parallel development instructions](instructions/parallel-development.instructions.md) and [review instructions](instructions/review.instructions.md). Parallel work is optional, not a substitute for sound task decomposition.
