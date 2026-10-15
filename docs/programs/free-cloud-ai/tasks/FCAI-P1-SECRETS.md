# FCAI-P1-SECRETS

## Objective

Implement Secret Service-backed credentials and lazy optional-package lifecycle

## Scope and acceptance

Repository: `runtime`. Status: `implementation-complete`. Owner: root. Model: coordinator not exposed. Coordinator controls transitions and integration. Dependencies: FCAI-P0-INVENTORY.

Encryption material stays in Secret Service; provider key stays in upstream encrypted SQLite. No plaintext persistence/argv/environment leakage. Private Node lifecycle and collision/failure/shutdown checks pass; real keyring acceptance remains required.

Permitted files: `free_ai/maslow_free_ai/**`, `free_ai/bin/**`, `free_ai/tests/test_runtime.py`.

## Checkpoint

Recorded 2026-10-11T15:56:05.839365+00:00. Implementation commits: e7b8831a4fc81f6fdf0a1b8369dcc748274d9112. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-source-package-checkpoint.json`.

Blocker: Real keyring/installed lifecycle acceptance unavailable..

Next action: Exercise actual locked/unavailable Secret Service in installed guest; recovery is separate.

Source, package and fixture results do not establish live provider/account access, hardware performance, physical audio or paired recovery. Candidate remains not-ready.
