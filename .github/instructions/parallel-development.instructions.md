---
description: "Use when coordinating parallel agents, builder-reviewer work, isolated branches, Git worktrees, task ownership, or integration."
---
# Parallel development and builder–reviewer workflow

## Plan and isolation

- Delegate only independently implementable work with a clear deliverable. The coordinator assigns each builder an exact, non-overlapping set of files, associated tests and any interface contract. One owner controls shared files such as dependency manifests, shared schemas, public interfaces, and integration tests.
- Give each builder a separate branch and Git worktree from the same agreed committed base. A branch cannot be checked out in two worktrees. Never have concurrent builders edit the same checkout or share ownership of a file. If scopes overlap, sequence the work or return the shared change to the coordinator.
- Each task brief specifies the base commit, absolute worktree path, allowed paths, acceptance criteria, test commands, dependencies, and output expected. Use repository-relative paths for ownership. Builders must not modify other worktrees or integrate other builders' changes.
- Worktrees require an existing Git repository and at least one commit. If either is absent, do not initialize, commit, or fabricate an isolated checkout without user authorization; use a single checkout and sequential, non-overlapping tasks instead. Worktrees share Git metadata, so they are not a security sandbox.
- Before creating a worktree, check `git status --short`, `git rev-parse --show-toplevel`, and `git rev-parse HEAD`. Agree how uncommitted changes will be handled; a worktree based on `HEAD` does not contain them. Do not discard, copy over, or silently omit user changes. Do not create a worktree or branch over an existing path or branch.
- Once authorized, the coordinator may run `git worktree add -b <new-branch> <new-absolute-path> <base-commit>`. Use the platform shell's quoting rules. Record the branch, base and path; do not delete worktrees or branches until integration is verified and the user has authorized cleanup.

## Build, review and integrate

1. Use a builder and a different reviewer agent or model when the runtime offers distinct choices. Use only available model identifiers; if independent review is unavailable, say so and review in a separate pass.
2. The builder implements only its assigned files, adds tests, runs targeted checks, and reports changed paths, results, caveats, and the uncommitted diff or authorized commit. Stop and request coordinator ownership if an unassigned file or contract change is needed.
3. Give the reviewer the task, acceptance criteria, base revision, candidate worktree or authorized commit, and test results. The reviewer inspects the actual candidate and does not edit the builder's files. Report findings with severity, path, line and rationale, or state that there are no findings plus residual risks.
4. The builder addresses accepted findings within its boundary. The reviewer verifies those fixes; the coordinator resolves disagreements and interface conflicts. Do not mark the task complete with unresolved material findings.
5. The coordinator integrates one candidate at a time, checking its diff and ownership before applying it. Coordinate shared-file edits centrally, preserve user changes, and use only an agreed transfer method: inspect/apply an uncommitted patch, or cherry-pick an authorized commit. Never commit, cherry-pick, reset, overwrite, remove or clean worktrees without the needed authorization.
6. Run cross-boundary integration tests and relevant regression checks in the integration checkout. Report conflicts, deferred review, tests not run, and the actual models used when known. A passing isolated builder test does not replace integration verification.

## Suggested boundaries

- Backend API: `src/netpulse/api/` and assigned API tests.
- Core/security: `src/netpulse/core/` and assigned core tests.
- Diagnostics: `src/netpulse/diagnostics/` and assigned probe/FSM tests.
- Storage: `src/netpulse/storage/` and assigned storage tests.
- Dashboard: `frontend/` and assigned frontend tests.

These are starting points, not automatic ownership of shared files. Agree on contracts before parallel implementation.
