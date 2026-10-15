# FCAI-P3-CONNECT

Implement accepted Connect package and exact-account authorization. Status `implementation-complete`; coordinator owns integration; independent reviewer uses actual gpt-6-astra/high.

Acceptance: Only exact user-selected read-only accounts are exposed; scope is verified before each action; revocation/disconnect removes access and blocks stale sessions; no default account discovery or writes.

Permittedfiles: `packages/bridge/src/managed-accounts*.ts`, `packages/bridge/src/accounts.ts`, `packages/bridge/src/cli.ts`, `packages/bridge/test/managed-accounts.test.ts`, `README.md`, `docs/managed-read-only-accounts.md`, `docs/evidence/2026-10-11-managed-accounts.json`.

Sourcecommits: 646aa1149f36050a470ded7e3658ad0b0a38bcbb. Evidence: `docs/programs/free-cloud-ai/evidence/2026-10-11-account-ui-source-checkpoint.json` and `docs/programs/free-cloud-ai/evidence/2026-10-11-account-recovery-review.json` (scope/limits differ).

Blocker: No accepted managed native package/root marker/liveaccount proof..

Accepted Craft source `2e872f50a28706e70c159380e2b7186869415b7f` is reconciled in a new isolated worktree `/home/maslow/Projects/Maslow/free-ai-connect-current`. Commit `97ac20eed146a8c6b37e33c2c29901a00f3045ff` replays the managed implementation; both previous worktrees remain unchanged. Combined owning checks pass 369 tests with ten existing environment skips, full typecheck and build. Independent review verifies 158 unaffected baseline files, the additive CLI route, unchanged managed implementation and lock. [Integration evidence](../evidence/2026-10-11-connect-current-integration.json) records exact hashes and limits.

Next action: Review the additive managed Connect package recipe, then prove native marker/closure and actual live metadata/binding/revocation. Craft native5 is an accepted bounded baseline, not managed-account acceptance.

No source/test/fixture establishes liveaccount, heardaudio, hardwareperformance, signedinstallation or pairedrecovery. Candidate remainsnot-ready.
