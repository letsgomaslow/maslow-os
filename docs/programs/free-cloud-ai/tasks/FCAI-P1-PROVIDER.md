# FCAI-P1-PROVIDER

## Objective

Implement Groq provider boundary for only gpt-oss-120b and gpt-oss-20b

## Scope and acceptance

Repository: `runtime`. Status: `verified`. Owner: provider_boundary. Model: gpt-6-astra/high. Coordinator controls transitions and integration. Dependencies: FCAI-P0-INVENTORY.

Every dispatch checks enabled provider/model policy; reject aliases, other models and provider fallback; validate from fetched and cached catalogs, stale/malformed/unavailable catalog behavior; no credential leakage.

Permitted files: `free_ai/router/**`.

## Checkpoint

Recorded 2026-10-11T15:56:05.839365+00:00. Implementation commits: e7b8831a4fc81f6fdf0a1b8369dcc748274d9112. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-boundary-review.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-source-package-checkpoint.json`.

Blocker: none for the scoped source gate; global installed/live gates remain open.

Next action: Retain software policy; require live route tool probes before setup readiness.

Source, package and fixture results do not establish live provider/account access, hardware performance, physical audio or paired recovery. Candidate remains not-ready.
