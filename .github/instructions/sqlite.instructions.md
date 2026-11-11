---
description: "Use when developing or reviewing SQLite schema, queries, migrations, retention, transactions, or storage code."
applyTo: ["**/*.sql", "src/netpulse/storage/**/*.py"]
---
# SQLite and persistence

- Follow the schema, retention, idempotency, WAL and shutdown contracts in `SPEC.md`. Make schema changes explicit and provide an upgrade path for existing databases when one exists.
- Bind SQL parameters; never interpolate untrusted values into SQL. Validate any dynamic identifiers against an allowlist.
- Use explicit transaction boundaries and atomically update related job and idempotency state. Roll back incomplete operations; never silently convert a storage error to success.
- Keep blocking SQLite work off latency-sensitive async paths. Bound batch sizes, account for concurrent readers and writers, close cursors and connections, and do not assume a WAL checkpoint is always safe or available.
- Test schema creation and migration, transaction rollback, concurrent access, restart recovery, retention boundaries and query ordering as relevant. Use temporary databases; never run destructive tests on a user's database.
