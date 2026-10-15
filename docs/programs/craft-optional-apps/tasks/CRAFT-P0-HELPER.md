# CRAFT-P0-HELPER

Objective: Implement standard-library ledger validation, serialized claims, status and resume packets.

Repository: runtime. Phase: 0. Dependency: CRAFT-P0-RECORDS.

Permitted implementation files: docs/programs/craft-optional-apps/manage.py and test_manage.py. Worker writes only this central report; coordinator owns ledger and integration.

Status: implementation-complete, pending coordinator review and integration.

## Attempt and source

Attempt 1, 2026-10-11. Owner/worker: records_helper, /root/records_helper. Session: 2026-10-11-craft-root. Actual model: gpt-6.1-sol, medium reasoning. Baseline: 098948e4. Worktree: /home/maslow/Projects/Maslow/craft-records-worker. Branch: codex/craft-records-helper. Scoped implementation commit: ae3a35e5 (Add serialized Craft ledger management helper). No shared records, ledger, development index or deployment settings changed by the worker.

## Changes

Added a Python standard-library JSON CLI with validate, status, claim and resume. Validation detects duplicate/invalid IDs, missing dependencies, cycles, malformed fields, repository-scoped hierarchical/glob ownership collisions, missing completion evidence, missing/changed SHA-256 artifacts and completed tasks with failed/error tests. Integrated predecessors alone make queued tasks dependency-ready; invalid ledgers expose no ready selection.

Claim requires owner, session, model and an existing worktree. Occupied/completed/unready tasks, unreconciled queued claim metadata and ownership conflicts fail before writes. A stable sidecar flock covers the full read/validate/modify sequence; same-directory temporary write, file fsync, atomic replacement and directory fsync preserve serialized updates. Claim is the only mutating command; status transitions remain coordinator-controlled.

Resume includes outstanding claims, owner/session/worker/model, worktree existence, baseline/branch/commits/checkpoint, evidence/artifact diagnostics, next actions and ready task records. It requires manual confirmation or interruption of live workers and Git/report/artifact reconciliation, with no timestamp-based reclaim or inference of worker liveness.

## Verification

- `python -m unittest discover -s docs/programs/craft-optional-apps -p test_manage.py -v`: 11 tests pass. Synthetic temporary ledgers cover graph errors, integrated dependency selection, hierarchical/glob/repository overlap, evidence and hash changes, completed failing tests, malformed inputs, interrupted recovery, unchanged bytes after rejected claims, and two-process same-task/disjoint-task claim races.
- `python docs/programs/craft-optional-apps/manage.py validate`: worker baseline ledger valid.
- `python docs/programs/craft-optional-apps/manage.py --ledger /home/maslow/Maslow-ai-os/maslow-os/docs/programs/craft-optional-apps/tasks.json --repo-root /home/maslow/Maslow-ai-os/maslow-os validate`: central ledger valid; one advisory for this active worker at the time of verification.
- `git diff --cached --check`: pass before the scoped commit. Worker checkout clean after commit.

No central record claims or synthetic evidence were created by tests. No graphical, package, installed-system or physical acceptance applies to this development helper change.

## Conventions and caveats

Evidence entries must be existing file paths or objects containing a path; relative evidence/artifact paths resolve against --repo-root (default: the helper's repository). SHA-256 artifact entries map paths to digests. Tests use objects containing check and result, with pass/fail/skip/error/unavailable results. Existing file presence does not itself verify evidence contents; coordinator review remains required.

Path globs support segment-local *, recursive **, ?, and fnmatch character classes. Literal ownership paths conservatively include their subtree, because this check must not depend on currently existing files. This can flag a literal file path treated as a possible directory; review ownership scopes if that occurs. Explicit coordinator_only: true intentionally excludes coordinator-only tasks from ownership collision checks; it does not bypass other validation.

flock is Linux/POSIX development tooling, not a portable scheduler or service. The sidecar lock must remain stable during concurrent claims; do not delete it while another claim can be running. JSON output and exit status 1 communicate invalid ledgers/rejected operations. Read-only recovery cannot establish worker liveness or verify Git commit existence; those checks are explicit coordinator actions.

Next action: coordinator review ae3a35e5, rerun focused tests and central validation, integrate accepted files, then record helper verification/integration in the ledger and evaluate CRAFT-P0-GATE.
