# FCAI-P3-CONNECT

## Objective

Implement accepted Connect package and exact-account authorization

## Scope and acceptance

Repository: `connect`. Status: `active`. Owner: boundary_review. Model: gpt-6-astra/high. Coordinator controls transitions and integration. Dependencies: FCAI-P1-HERMES.

Only exact user-selected read-only accounts are exposed; scope is verified before each action; revocation/disconnect removes access and blocks stale sessions; no default account discovery or writes.

Permitted files: `src/**`, `test*`, `docs/**`.

## Checkpoint

Recorded 2026-10-11T15:56:05.839365+00:00. Implementation commits: none recorded. Evidence: pending worker report.

Blocker: Managed session and live exact-account proof not yet available..

Next action: Prove SDK exact account dispatch binding, then managed read-only session and revocation tests.

Source, package and fixture results do not establish live provider/account access, hardware performance, physical audio or paired recovery. Candidate remains not-ready.
