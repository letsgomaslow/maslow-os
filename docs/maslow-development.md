# Maslow AI-OS development: start here

## ISOLATED EVALUATION — current Omarchy candidate, 2026-10-17

The [isolated quattro handoff](handoffs/2026-10-17-quattro-candidate.md) records source integration, corrected package builds, passing Hub/Voice visual checks and an unresolved installed lock-surface failure. Maslow main and the accepted installed preview remain unchanged. Do not build a release ISO or move to destructive native installation from this result. Next: diagnose the black locked surface using the exact current Quickshell/Qt distribution stack and a disposable control, then repeat visible lock and normal unlock acceptance.

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

- [Isolated current Omarchy candidate, October 17](handoffs/2026-10-17-quattro-candidate.md): pinned development merge, exact artifacts, source failures/retakes, installed Hub/Voice visual evidence and the lock gate.
- [Current Hub/Voice VM and upstream audit, October 17](handoffs/2026-10-17-current-vm-upstream.md): preserved current-product baseline, separate Hub fresh-state correction and initial upstream comparison.
- [2012 Retina MacBook Pro local VM check, October 17](handoffs/2026-10-17-macbook-2012-vm.md): historical installed-image/CPU-emulation evidence and physical-hardware limits.

- [Hub 2 native preview and archived development index](handoffs/2026-10-13-hub-2-native-preview.md): current installed receipts first, followed by preserved signing, recovery, design and earlier workstream history. Historical “current” and “next” labels are not present instructions.
- [Repository ownership and Lenovo setup](lenovo-development.md): source topology; inspect current Git refs before integration.
- [Voice development/testing guide](../agents/skills/voice-development.md): provider, audio and execution acceptance boundaries.
- [September 5 hardware installation evidence](handoffs/2026-09-05-verified-usb-native-acceptance.md) and [support readiness](handoffs/2026-09-12-support-readiness-closeout.md): older ISO/hardware evidence, not proof that the new Hub is in a rebuilt installer or a public release.
