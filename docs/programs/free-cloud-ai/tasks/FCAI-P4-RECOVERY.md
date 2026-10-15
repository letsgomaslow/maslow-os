# FCAI-P4-RECOVERY

Exercise full database, key and package recovery. Status `active`; owner root; actual model coordinator not exposed.

Acceptance: Document and execute backup/restore, missing/corrupt database, lost/rotated key, package missing/partial install/upgrade/rollback, interrupted operations and idempotent retry; preserve user data and fail closed.

Permitted files: `free_ai/maslow_free_ai/recovery.py`, `free_ai/maslow_free_ai/runtime.py`, `voice/maslow_voice/free_ai_delivery.py`, `voice/maslow_voice/daemon.py`, `voice/maslow_voice/tasks.py`, `free_ai/tests/test_recovery.py`, `free_ai/tests/test_runtime.py`, `voice/tests/test_free_ai_delivery.py`, `voice/maslow_voice/store.py`, `voice/maslow_voice/ipc.py`, `free_ai/tests/secret_service_probe.py`.

Source commits: `f63cdb67`, `90c0745a`, `784eca20`, `b192d593`, `9a90e545`, `76fb5d08ca65662be1b16da1cce1eb0eee13f37b`.

Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-account-ui-source-checkpoint.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-account-recovery-review.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-runtime-delivery-review.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-delivery-recovery-checkpoint.json`, `docs/programs/free-cloud-ai/evidence/2026-10-11-hub-stage1-checkpoint.json`.

Blocker: Privileged interrupted package/database/key restoration, fresh-install undo and installed systemd/guest/hardware/live gates remain unverified. Historical restore after admission resumes is deliberately unavailable.

Guarded Hub source `2a8c6eda15d92078fdd8656a879b1e93dd786a1d` now passes scoped independent review and230owning/77focused/UI/22original/30recovery component checks. [Checkpoint](../evidence/2026-10-11-hub-recovery-source-checkpoint.json) binds exact hashes and synthetic-service/inert-package limits. Both public gates remain false.

Next action: Build the exact supported package pair when the shared Craft workload settles, then prove actual native package/database/key restoration and fresh undo before enabling delivery. Preserved state with the package absent remains an unsupported reinstall gate.

Source tests and synthetic service/package fixtures cannot establish live accounts, heard audio, installed hardware, signed delivery or paired package recovery. The candidate remains not-ready.
