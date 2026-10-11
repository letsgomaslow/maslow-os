# FCAI-P4-RECOVERY

Exercise full database, key and package recovery. Status `active`; owner root; model coordinator not exposed.

Acceptance: Document and execute backup/restore, missing/corrupt database, lost/rotated key, package missing/partial install/upgrade/rollback, interrupted operations and idempotent retry; preserve user data and fail closed.

Permittedfiles: `free_ai/maslow_free_ai/recovery.py`, `free_ai/maslow_free_ai/runtime.py`, `voice/maslow_voice/free_ai_delivery.py`, `voice/maslow_voice/daemon.py`, `voice/maslow_voice/tasks.py`, `free_ai/tests/test_recovery.py`, `free_ai/tests/test_runtime.py`, `voice/tests/test_free_ai_delivery.py`.

Sourcecommits: f63cdb67, 90c0745a, 784eca20. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-account-ui-source-checkpoint.json` and `docs/programs/free-cloud-ai/evidence/2026-10-11-account-recovery-review.json` (scope/limits differ).

Blocker: User-owned current-operation snapshot/restore source passes; rootpairedinstallation/actualinterruption/historicalrollback gates remain open..

Next action: Implement root-ticket reader and prepare/check RPC that closes all task/conversation/configuration admission; coordinate exactcontract withAstra Hubworker.

No source/test/fixture establishes liveaccount, heardaudio, hardwareperformance, signedinstallation or pairedrecovery. Candidate remainsnot-ready.
