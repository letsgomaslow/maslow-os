# FCAI-P3-CONNECT

Implement accepted Connect package and exact-account authorization. Status `implementation-complete`; owner boundary_review; model gpt-6-astra/high.

Acceptance: Only exact user-selected read-only accounts are exposed; scope is verified before each action; revocation/disconnect removes access and blocks stale sessions; no default account discovery or writes.

Permittedfiles: `packages/bridge/src/managed-accounts*.ts`, `packages/bridge/src/accounts.ts`, `packages/bridge/src/cli.ts`, `packages/bridge/test/managed-accounts.test.ts`, `README.md`, `docs/managed-read-only-accounts.md`, `docs/evidence/2026-10-11-managed-accounts.json`.

Sourcecommits: 646aa1149f36050a470ded7e3658ad0b0a38bcbb. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-account-ui-source-checkpoint.json` and `docs/programs/free-cloud-ai/evidence/2026-10-11-account-recovery-review.json` (scope/limits differ).

Blocker: No accepted managed native package/root marker/liveaccount proof..

Next action: Reconcile additive CLI/accounts changes with accepted Craft lifecycle source before native package; require actual live metadata/binding.

No source/test/fixture establishes liveaccount, heardaudio, hardwareperformance, signedinstallation or pairedrecovery. Candidate remainsnot-ready.
