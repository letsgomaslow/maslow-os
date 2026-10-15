# FCAI-P1-HERMES

## Objective

Constrain Hermes tools, dispatch contract and request idempotency

## Scope and acceptance

Repository: `runtime`. Status: `verified`. Owner: root + boundary_review + work_ui_check. Model: gpt-6-astra/high; gpt-6.1-sol/medium. Coordinator controls transitions and integration. Dependencies: FCAI-P0-INVENTORY.

Typed questions/drafts and explicit new notes use only managed tools with immutable contract/idempotency and checked receipt. This source gate excludes account access (separate Connect task) and live model usefulness.

Permitted files: `voice/**`, `free_ai/tests/hermes*`.

## Checkpoint

Recorded 2026-10-11T15:56:05.839365+00:00. Implementation commits: e7b8831a4fc81f6fdf0a1b8369dcc748274d9112. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-source-package-checkpoint.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-hermes-runs.json`.

Blocker: none for the scoped source gate; global installed/live gates remain open.

Next action: Integrate Connect grants additively; reverify changed profile/task/UI and rebuild candidates.

Source, package and fixture results do not establish live provider/account access, hardware performance, physical audio or paired recovery. Candidate remains not-ready.
