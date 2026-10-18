# Maslow AI-OS development: start here

## ISOLATED EVALUATION — current Omarchy candidate, 2026-10-17

The [new frozen ISO lifecycle handoff](handoffs/2026-10-17-new-iso-lifecycle.md) records a newly assembled internal ISO, independent media admission (2,672 checks; all 1,305 indexed package archives verified), actual fresh installation on a blank VM disk, independent disk-only boot and first app installation before update. The final Hermes 0.22.2-4 / Voice 0.1.5-47 pair is present directly on the media. The actual Arch VM ISO source suite passes all 15 shell groups and 187 Python tests; later ISO test-only commits do not change the tested media bytes. Main remains unchanged.

The same fresh system passes the supported updater under the four runtime package holds, a new updated kernel boot, genuine Limine snapshot boot and the supported full root restore to a normal writable root with its exact pre-update package vector. The newer home Node environment survives rollback. Fresh, updated and restored settled Hub/Voice views and actual isolated Hermes profiles pass, with earlier failures retained. The same supported updater also passes reapply with the newer home preserved, followed by actual updated-kernel boot and final settled Hub/Voice/profile checks. Four-stage health/ledger/source hashes match, and normal shutdown plus closed artifact hashes pass. Next: fix and regression-test Claude auth supervision in a separate candidate, retaining this ISO and its startup failures. Remaining gates include intermittent default cold shell readiness, Claude canonical status supervision, signing, encrypted/factory recovery, real providers/audio and physical MacBook acceptance. The [blocker integration](handoffs/2026-10-17-iso-blocker-integration.md), [earlier lifecycle](handoffs/2026-10-17-install-update-rollback.md) and [Qt/lock handoff](handoffs/2026-10-17-qt612-stack-lock.md) retain their historical exact inputs. This internal ISO is the frozen candidate, not a claim of global latest upstream or a signed release. No merge, publication or physical erase occurred.

## CURRENT — accepted installed preview, 2026-10-15

Hub **2.0.3-1**, Voice **0.1.5-44**, and Free AI **0.1.0-3** are installed and ready for user testing. Canonical Hub rollback to 2.0.2 and verified reapply to 2.0.3 passed; the owning updater is idle with no transaction, and native Updates shows “Up to date”. Each transaction preserved all **8 tasks, 494 events and five preference files**. Original idle settings were restored. Exact source/build revisions, the 754-test/UI result, design requirements and remaining proof limits are in the [accepted Hub 2 baseline](hub-2-baseline.md); detailed receipts and prior cursors are in the [dated handoff](handoffs/2026-10-13-hub-2-native-preview.md). Next: user tests the installed branded preview. No authentication or rollback gate remains from this roundtrip.

## Resume safely

The [source integration closeout](handoffs/2026-10-15-hub-2-main-integration.md) records Hub/runtime `main`, scoped packages `maslow`, future-agent entry points, separately backed-up Connect WIP and the hosted-CI billing limitation. Source merge status and installed acceptance remain separate facts; use the product branches for subsequent iterations.

1. Read [AGENTS.md](../AGENTS.md), the [baseline](hub-2-baseline.md), and the owning repository instructions before changing anything. Preserve the accepted prototype-aligned Hub design, official logo and Manrope; keep Voice UI/audio and security boundaries intact.
2. Run `git status --short --branch`, `git log -5 --oneline`, and `git worktree list` in each repository being touched. Rediscover active worktrees rather than following historical feature-branch names. The [repository map](lenovo-development.md) documents ownership; its dated checkout examples are historical.
3. Keep installed versions, tested product revisions, later documentation commits, branch integration and publication distinct. Runtime and Hub product branches are `main`; packages and ISO use `maslow`. Integration/push status must be checked in Git, not inferred from installed acceptance.
4. Select one scoped task with an owning repository and acceptance criteria. Connect delivery remains gated and Craft paused. Live provider/audio acceptance and the broader Free AI program remain separate workstreams.
5. Record focused checks, exact revisions, failures and remaining gates. Do not repeat signing, privileged operations or expensive acceptance merely because a historical cursor mentions them.

## Evidence and historical work

- [New frozen ISO and installed lifecycle, October 17](handoffs/2026-10-17-new-iso-lifecycle.md): exact newly assembled media, independent audit, fresh install, supported update, genuine snapshot/full restore and runtime gates.
- [ISO blocker integration, October 17](handoffs/2026-10-17-iso-blocker-integration.md): exact frozen sources/artifacts, translation and sudo parity, corrected Hermes/Voice packages, integrated installer evidence and remaining cold-start/new-media gates.
- [Installation, migration, update and rollback evaluation, October 17](handoffs/2026-10-17-install-update-rollback.md): exact candidate lifecycle evidence, scoped fixes and remaining ISO/native gates.
- [Current Quickshell / Qt 6.12 installed retest, October 17](handoffs/2026-10-17-qt612-stack-lock.md): exact signed dependency stack, corrected lock controls, source reruns, installed Hub/Voice lifecycle evidence and remaining gates.
- [Isolated current Omarchy candidate, October 17](handoffs/2026-10-17-quattro-candidate.md): pinned development merge, exact artifacts, source failures/retakes, installed Hub/Voice visual evidence and the historical lock diagnosis corrected by the later retest.
- [Current Hub/Voice VM and upstream audit, October 17](handoffs/2026-10-17-current-vm-upstream.md): preserved current-product baseline, separate Hub fresh-state correction and initial upstream comparison.
- [2012 Retina MacBook Pro local VM check, October 17](handoffs/2026-10-17-macbook-2012-vm.md): historical installed-image/CPU-emulation evidence and physical-hardware limits.

- [Hub 2 native preview and archived development index](handoffs/2026-10-13-hub-2-native-preview.md): current installed receipts first, followed by preserved signing, recovery, design and earlier workstream history. Historical “current” and “next” labels are not present instructions.
- [Repository ownership and Lenovo setup](lenovo-development.md): source topology; inspect current Git refs before integration.
- [Voice development/testing guide](../agents/skills/voice-development.md): provider, audio and execution acceptance boundaries.
- [September 5 hardware installation evidence](handoffs/2026-09-05-verified-usb-native-acceptance.md) and [support readiness](handoffs/2026-09-12-support-readiness-closeout.md): older ISO/hardware evidence, not proof that the new Hub is in a rebuilt installer or a public release.
