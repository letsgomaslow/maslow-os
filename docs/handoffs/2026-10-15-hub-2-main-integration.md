# Hub 2 source integration and future-agent baseline

The user authorized documenting the completed work, committing it and merging the accepted Hub2 baseline into product branches. Source integration is separate from the installed local preview and from release publication. Start future iterations from current product branches and [the accepted baseline](../hub-2-baseline.md); do not restore older feature worktrees, visual prototypes or historical pending prompts.

## Repositories and merge records

| Repository | Product branch | Integration |
| --- | --- | --- |
| `maslow-hub` | `main` | [PR3](https://github.com/letsgomaslow/maslow-hub/pull/3), merge `8ee94f79a9aa719a6b963eb89fcc9e2b513b2a65`, including baseline documentation `eba54903c7ef3d0887b179b5e7edd6d13bb9d961` |
| `maslow-os-pkgs` | `maslow` | [PR7](https://github.com/letsgomaslow/maslow-os-pkgs/pull/7), merge `9d23b67c3f28a2544a111ad4288c911177ede829`, scoped recipe commit `89f7b6b725312b873bf7b39420f870087f2e1899` |
| `maslow-os` | `main` | [PR19](https://github.com/letsgomaslow/maslow-os/pull/19) integrates the accepted runtime lineage, agent-entry documentation `1310bff8` and this closeout; the PR's merge receipt is authoritative for its final SHA/status |

The Hub/runtime branches were descendants of their existing product refs, so their accepted history is retained. This runtime lineage includes the earlier `maslow` CLI naming, system-package download retry and paused Craft baseline; it is not a Voice-only merge. No ISO source/build change belongs to this integration.

Packages use `maslow`, not `main` or upstream `master`. The isolated packaging branch takes exactly the19 reviewed tracked files in Hub/Voice/Free AI directories from6a681df, with the three backend3 inputs from18d0e10; only two README status notes differ intentionally. Recipe/tool/data bytes and modes match, retaining Voice44 sourcea8afb84f and backend3 sourcea41012c6 plus their exact archive pins. Unfinished Connect recipe changes/history are excluded.

## Documentation and verification

All three owning repositories update AGENTS.md, README and durable baseline guidance. Hub also corrects stale UI/package-layout references, feature placement and historical visual notes. Runtime has one CURRENT index; prior historical prose is archived in the dated handoff, with the old opening summary replaced by the accepted current status. Baselines preserve official MASLOW | AI-OS identity, Gradient Bridge, existing Manrope, six native journeys, existing Voice ownership, private credentials, truthful availability and signed update/recovery boundaries. They explicitly allow focused future iterations while preventing accidental reversion.

Validation for source integration:

- Hub executable/UI source is unchanged from frozen93458a5; retained754 Python tests pass with no skips/failures. Fresh UI contracts and diff checks pass. Runtime `voice/` matchesa8afb84f and `free_ai/` matchesa41012c6 exactly; existing owning/native evidence remains applicable.
- Runtime brand validation, inherited `maslow` command tests, package-download retry tests and Hub routing tests pass.
- Scoped packages pass exact19-file/mode comparison, all three recipe syntax checks, downstream packaging invariants, backend recipe9 tests, Voice source-tool6 tests and both source validators against retained exact inputs. An initial Voice-test invocation used `-B`, preventing the fixture's expected bytecode creation; the unchanged suite passes in its required normal mode. No validator/test was weakened.
- Relative Markdown links, referenced product revisions, staged scope and `git diff --check` pass. No unchanged package/ISO build or full owning suite was repeated for documentation-only changes.
- GitHub-hosted checks were attempted: [Hub run](https://github.com/letsgomaslow/maslow-hub/actions/runs/38808617669) ended startup_failure with no jobs, and [package run](https://github.com/letsgomaslow/maslow-os-pkgs/actions/runs/38808617371) could not start any test steps because the account was locked by a billing issue. Hosted CI is unavailable, not passing. Local owning checks and independent review support this source integration; no protection/check was disabled. Resolve account billing before relying on future hosted runs.

The [baseline](../hub-2-baseline.md) and [installed handoff](2026-10-13-hub-2-native-preview.md) retain exact product/package hashes, native fixtures versus installed proof, normally authenticated rollback/reapply,8/494/5 preservation, same-shell continuity, restored idle settings and remaining P2/coverage limits. Merging source does not replace or rebuild those tested artifacts.

## Separately preserved Connect WIP

At the user's explicit request, seven pre-existing files were saved unchanged in `maslow-hub` branch `codex/connect-wip-2026-10-15`, commit `112b71e86e97e934a41a92091934e89992de32ee`, with one additional WIP checkpoint. Before/staged/after hashes match; a bounded credential-pattern scan found no matches. The branch was pushed for backup and is **not merged into the Hub2 baseline**. Original `codex/free-cloud-ai-hub-current` remains at2bf25ef. No functional tests/acceptance are claimed for this preservation-only commit. Future Connect work requires review against current Hub main; copying its old AGENTS/README or restoring that branch as the Hub baseline is incorrect.

Other pre-existing runtime research/docs changes and an untracked error.log belong to different worktrees and remain untouched. Machine-local preservation/merge evidence stays outside Git in `hub-2-build/merge-prep/`; do not commit raw logs, credentials, package caches or personal task data.

## Where the next agent should begin

Use Git status/log/worktree inventory and current remote refs. Product checkouts in this workspace are `/home/maslow/Projects/Maslow/maslow-hub-main` (`main`), `/home/maslow/Maslow-ai-os/maslow-os-main` (`main`) and `/home/maslow/Projects/Maslow/maslow-os-pkgs` (`maslow`). Historical dirty/feature checkouts were preserved, not reset or replaced. These paths are workspace navigation, not portable build inputs.

Choose one scoped user iteration, preserve Hub2 identity/journeys and existing backend/Voice/account/security ownership, and record new source/checks/limits in the current index and owning handoff. Keep all four tracked V1/V2 acceptance flags closed, Connect delivery gated and Craft paused. No packages, ISO, public release assets, credentials or signing material were published; user authorization here concerns source commits/merges only.
