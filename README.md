# NetPulse Local

NetPulse Local is a planned local network diagnostics daemon and web dashboard.
The requirements and phased acceptance gates are in [SPEC.md](SPEC.md).

## Project layout

- `src/netpulse/` — Python daemon package:
  - `api/` — REST and WebSocket interfaces.
  - `core/` — configuration, security, clocks, and tracing.
  - `diagnostics/` — probes and diagnostic state machines.
  - `storage/` — SQLite persistence and retention.
- `frontend/` — browser dashboard assets.
- `tests/` — automated tests.

## Development setup

Requires Python 3.11 or later. From the project root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m unittest discover -s tests
```

On macOS or Linux, use `python3 -m venv .venv` and
`.venv/bin/python` in place of `.\.venv\Scripts\python`.

This is an initial skeleton, not a working diagnostics application. No server
entry point is provided yet: localhost authentication and hardening must be
implemented before exposing the API or dashboard.

Agent and parallel-work rules: [.github/copilot-instructions.md](.github/copilot-instructions.md).
