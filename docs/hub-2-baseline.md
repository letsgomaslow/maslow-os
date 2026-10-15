# Accepted Hub 2 baseline

Accepted installed Lenovo preview, 2026-10-15: **Hub 2.0.3-1 / Voice 0.1.5-44 / Free AI 0.1.0-3**. The next action is user testing of the installed branded preview. Local signed-preview acceptance, source integration and publication are distinct; [the integration closeout](handoffs/2026-10-15-hub-2-main-integration.md) records the product-branch merges and future-agent entry points. No public release, stable channel or ISO rebuild is implied.

## Product and design contract

Hub has six native journeys: Home, Work, Connections, My context, Apps, and Settings. Preserve the supplied prototype-aligned presentation, official Gradient Bridge / MASLOW | AI-OS lockup and canonical Manrope typography with native dark/light/accent palettes. The user rejected the earlier old-Hub-like presentation and monospace typography; do not reintroduce them as a cleanup or theme fix. Branding source and terms are in [branding](../branding/README.md). Preserve keyboard focus reveal, compact layout constraints, truthful loading/error feedback, real task selection and existing action reachability.

Hub wraps existing supported functionality. Preserve the standalone Voice UI and audio implementation, exact-task/composer/settings handoffs, private credential stdin handling, active-session guards, delivery/recovery barriers and owning updater admission. Do not turn passive status into provider calls, expose credentials, bypass permissions, or interpret this preview as authorization to redesign providers/backends. Connect V2/product gates remain closed; local QA exports do not promote them. Craft remains paused. Account readiness, provider sign-in and elevated consent are distinct.

## Exact provenance

| Input | Accepted revision / artifact |
| --- | --- |
| Hub product source | `93458a5d7ad9c7a34a7c2ecca298b9611ced4a39` |
| Voice product source | `a8afb84f21dfd03a15730f7c4c08b1e2ac4551da` |
| Hub package recipe | `6a681df2e8b4df0f62c26bcb3022602281a6db29` |
| Free AI backend 3 source | `a41012c6b207ac912eb034b813834485efe094f9` |
| Backend3 recipe correction | `18d0e104465e3d78bd00c932625d058ca4fa9c9a` |
| Hub archive SHA-256 | `ac9f734f6305e03c91d8d89a03ac410894d733afcd53fdc625270e09efa00ab7` |
| Local signed manifest sequence 16 SHA-256 | `8ef3d36b245384107fa10e05518acdbfa3269b3acd8d834467f0940c6def36d0` |

Later documentation commits do not change these tested package bytes. The dated local manifest is provenance, not an evergreen assertion of metadata validity or a published channel. Runtime/Hub product branches are `main`; package/ISO product branches are `maslow`. Discover current refs and worktrees before integration; source merge, package installation and publication require separate evidence.

Source integration includes the runtime lineage's earlier `maslow` CLI naming and system-package download retry, plus the paused Craft baseline; it is not a Voice-only merge. Scoped packaging consumes only Hub/Voice/Free AI recipe directories plus the backend3 correction, leaving unfinished Connect packaging separate. All four tracked V1/V2 install/recovery acceptance flags remain closed; the two supervised local V1 QA export changes do not become product defaults.

## Accepted verification

- Exact-fixture owning Python suite: **754 tests, zero failures and zero skips**; UI contracts passed. A prior host run had one fixture skip and is not substituted for the final exact-fixture result.
- Canonical, normally authenticated Hub rollback to 2.0.2 completed in **47.602 seconds**; independently reviewed verified reapply to 2.0.3 completed in **71.987 seconds**. Both preserved all **8 task rows, 494 event rows and five preference files** exactly.
- Native Updates reopened at 2.0.2 with verified 2.0.3 available, then at 2.0.3 with “Up to date”, on the same shell process. Final owning updater state is **idle / transaction null**; the earlier interrupted notice was reconciled by the owning rollback/apply, without manually clearing state.
- Real Quickshell fixtures cover dark/light/accent and compact/enlarged views, keyboard navigation and private-dialog behavior. Installed checks cover official branding, Name/URL/Icon focus reveal, enlarged Connections heading/account wrapping, an unsaved Name draft retained through a Light change and safely cleared, plus existing type composer, native settings and exact saved-task handoffs. No new task, provider request or account approval was submitted for these UI checks.
- Original palette/config/window state and idle settings were restored; idle enabled, stay-awake false, and no QA sentinel remained. Floor **16** enforcement was checked inside the admitted owning transaction: this is not broad downgrade authority or evidence that admission/recovery barriers may be bypassed.

The local evidence root is `hub-2-build/install-goal/installed-verification/` under the development workspace. `native-203-complete.json` indexes the preservation, native roundtrip and idle-restoration receipts. The [dated handoff](handoffs/2026-10-13-hub-2-native-preview.md) retains detailed inputs, earlier failures and review/admission provenance. These machine-local artifacts are not portable repository links or public release assets.

## Remaining limits

The enlarged compact sidebar's static footer clips (P2; navigation remains usable). Enlarged Connections heading/account copy was inspected natively, but its bottom disclosure has fixture-only coverage. The pre-existing stale aggregate desktop-lock state after unlock may recur; normal owning shell restart repaired observed instances, not the underlying OS issue. Physical audio, live provider acceptance and broader Free AI program acceptance remain separate; none is implied by UI contracts or these Hub transactions. The older ISO/hardware baseline is not replaced by this local package acceptance.
