# CRAFT-P0-INVENTORY

Objective: reconcile repository baselines, preserved changes, worktrees, tools and ISO harness availability. Review coverage of all 12 apps and the approved plan. Do not run product programs or change installed configuration.

Repository: runtime records, with read-only inspection of sibling source repositories.

Permitted files: this report only. Coordinator owns all other program files.

Dependencies: CRAFT-P0-RECORDS persisted before dispatch.

Acceptance: exact revisions/branches/worktrees and dirty paths recorded; ISO location or concrete access failure; available tools and platform evidence; any record omissions reported.

Owner: inventory worker. Model: gpt-6-luna, medium, if available. Attempt: 1.

Status: implementation-complete. Baseline: runtime worktree `/home/maslow/Maslow-ai-os/maslow-os`, branch `codex/craft-optional-apps`, HEAD `098948e42fa7ac0c3769402ae83a7bdc7d37cf05` (plan/records commit). Read-only inventory completed 2026-10-11. No product app or ISO program was executed and no installed configuration was changed.

## Repository and worktree inventory

| Repository / worktree | Branch and exact HEAD | Status / preserved state |
| --- | --- | --- |
| Runtime `/home/maslow/Maslow-ai-os/maslow-os` | `codex/craft-optional-apps`, `098948e42fa7ac0c3769402ae83a7bdc7d37cf05` | At initial capture: modified `docs/maslow-development.md`, `docs/programs/craft-optional-apps/tasks.json`; untracked `docs/handoffs/2026-10-11-freellmapi-review.md` and `docs/handoffs/2026-10-11-storytold-app-review.md`. The coordinator confirmed the ledger edits are current program work, not user changes. During concurrent coordinator work, `docs/handoffs/2026-10-11-craft-optional-apps.md` also appeared untracked; not touched by this worker. |
| Runtime integration `/home/maslow/Maslow-ai-os/maslow-os-gemini` | `codex/gemini-live-voice-closeout`, `b993e17fc230aee8386dfe295f28968dff55fd15` | Clean. |
| Connect `/home/maslow/Projects/Maslow/maslow-connect` | `codex/local-connect`, `0c6f7b98a062870e36503f55512d04e0b8576a69` | Clean; tracks `origin/codex/local-connect`. |
| Hub `/home/maslow/Projects/Maslow/maslow-hub` | `codex/hub-0.3.6-health`, `33940d2e8740b172b953cc3e091cbae1ba1cd303` | Clean; tracks `origin/codex/hub-0.3.6-health`. |
| Packages `/home/maslow/Projects/Maslow/maslow-os-pkgs` | `maslow`, `448856485e710caedfc24f544a027aea8652dd33` | Clean; tracks `origin/maslow` and `origin/HEAD`. |
| Releases `/home/maslow/Projects/Maslow/maslow-releases` | `codex/local-release-workstation`, `140e023baf4fccb651ca944a866af36b81b651b2` | Clean; tracks `origin/codex/local-release-workstation`. |
| ISO `/home/maslow/Projects/Maslow/maslow-os-iso` | `codex/maslow-hub`, `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb` | Was absent; `origin/codex/maslow-hub` was available and was cloned from the documented runtime URL. New checkout is clean. Product branch `maslow` also exists remotely at `905b26c47f314dd32245b85a0eaa0bf9d66f01bb`; this inventory uses the prescribed development branch. |

Other runtime worktrees and their inspected status:

| Worktree | Branch and exact HEAD | Status / preserved state |
| --- | --- | --- |
| `/home/maslow/Projects/Maslow/craft-records-worker` | `codex/craft-records-helper`, `098948e42fa7ac0c3769402ae83a7bdc7d37cf05` | Active helper worker's untracked `docs/programs/craft-optional-apps/manage.py`; preserved. |
| `/home/maslow/Projects/Maslow/maslow-os-docs` | `codex/progress-2026-10-10`, `3057b57e8505eeb9961ccb04032493ae7f4ad2ea` | Clean. |
| `/home/maslow/Projects/Maslow/maslow-os-qt612` | `codex/qt612-theme-color-local`, `4c463edb80d4cf353e41b96d8fa9095499ad7be7` | No tracked/untracked paths reported; branch has no upstream shown. |
| `/home/maslow/Projects/Maslow/maslow-os-qt612-main` | `codex/qt612-theme-color`, `23abd8d7a9d2b9db3d8debcffd00a842ec8bee40` | Clean. |
| `/home/maslow/Projects/Maslow/maslow-os-r2077` | detached, `dca4d9c824f958719c54c1ac09db0ffd82e89b68` | No tracked/untracked paths reported. |

These were inspected read-only. The helper worker's file is assigned work and was not touched. The runtime's own status shows no edits to any task report other than this worker's permitted report.

The source-map documentation specifies product branches runtime `main`, packages `maslow`, ISO `maslow`, Hub `main`; the checked-out feature branches above are development baselines and must not be mistaken for product integration. Connect and releases are separate repositories and are not part of the three-repository ISO build chain.

## Host and prerequisite availability

Host is x86_64 Linux, kernel `7.2.9-arch1-1`, `/etc/os-release` identifies Maslow OS `0.1.0-preview.1`.

| Tool | Availability |
| --- | --- |
| `node` | Present, v26.11.1 |
| `pnpm` | Direct command missing; `npx --yes pnpm@10.33.3 --version` resolves v10.33.3. The coordinator reports a frozen install passed using this path; this worker did not run an install. |
| `bwrap` | Present, 0.13.0 |
| `makepkg` | Present, pacman 7.1.0 |
| `docker` | Present, 29.9.0; daemon/build readiness not checked |
| `qemu-system-x86_64` | Missing |
| `qemu-img` | Missing |

The ISO harness is located at `maslow-os-iso/bin/omarchy-iso-test`; shared unattended VM machinery is `maslow-os-iso/test/integration.d/base-test.sh`; usage, artifacts, and reuse options are documented in `maslow-os-iso/docs/installer-reference.md`. It performs a real ISO install in headless QEMU, drives screens through QMP/OCR and virtual keys, uses generated CIDATA, and retains screenshots/logs and a reusable installed base disk. Harness was located only; it was not run. Missing QEMU binaries block local execution on this host. Docker is documented for image assembly and is available by command lookup; no ISO build was attempted. The current host is a suitable x86_64 Linux platform in architecture/OS terms, but not currently equipped for VM acceptance.

The coordinator additionally reports that `bwrap` passed a host `unshare-all` smoke check with a minimal `/usr/lib64` symlink case. This is coordinator-provided evidence, not a test run by this inventory worker; it does not establish app-specific confinement.

## App and program coverage review

All 12 app records exist and align with the requested sequence: PdfCraft, PhotoCraft, VectorCraft, WordCraft, GridCraft, DeckCraft, LightCraft, EffectCraft, FilmCraft, DesignCraft, CADCraft, SoundCraft. Each record includes a reviewed release target, repository link, package/compatibility/confinement/workflow gates, experimental evaluating status, and task-report pattern. The program README separates package, GUI/CLI, confinement, MCP, Voice, and disposition work, preserves the pilot order, and says package builds alone do not establish integration. It also limits the offer to optional x86_64 Maslow/Hyprland apps and Connect, with project/output roots and selected agents; excludes live-window automation, ISO/base-package bundling, public promotion, and production signing/publication from this scope.

The prior Storytold review covers all 12 source snapshots and the supporting repository dispositions. Material known constraints include: source-visible MCP is not confinement; many apps lack usable file-root flags, and selection flags are not a sandbox; several local TCP GUI bridges are unauthenticated, so the planned v1 path must avoid them; selected project files can reach the configured model/provider; GUI and headless saved-file workflows are separate; some workspaces require Rust 1.95 despite lower crate declarations; Linux/Windows testing is thinner than macOS for several apps; and upstream fidelity/feature gaps vary substantially (including XLSX loss and limited real-workbook corpus coverage, incomplete PPTX fidelity, RAW camera support, video codec/performance and project-import gaps, page-layout/IDML limitations, CAD DWG loss and incomplete core workflows, and incomplete audio device/recording/interchange support). The reviewed research is source-level and does not establish installed Maslow behavior.

Record omission to resolve at app-evaluation time: the 12 short app records currently repeat the same generic package, confinement, and workflow gates and retain only the reviewed release tag. They do not carry each app's concrete upstream limits or the corresponding accepted/rejected fidelity cases from the research handoff. This is not a Phase 0 omission because the handoff contains the findings, but each app record should receive concise, app-specific blockers and reconsideration conditions as its dependency-ready task is evaluated. No final deferrals/exclusions are yet evidenced; all remain `evaluating`, which matches the plan.

The checked ledger has 88 unique task IDs: six app-specific work items for each of the 12 apps (72 total), plus foundation, phase, and release tasks. `CRAFT-P0-RECORDS` is recorded integrated at `098948e4`; `CRAFT-P0-GATE` depends on the records, inventory, and helper, followed by pilot package tasks. No missing app is visible in the task/report coverage. Existing dirty runtime documentation and ledger files are coordinator-owned and were left untouched.

## Evidence and next action

Evidence: `git status --short --branch`, `git log -1`, and `git worktree list` on runtime and requested sibling repositories; targeted `git ls-remote` verified the ISO development branch before cloning; ISO `AGENTS.md`, `README.md`, and installer harness documentation inspected; command availability and platform identified. No tests or product programs were run. No secrets or raw logs were collected.

Next action: coordinator validates helper/records and closes Phase 0; QEMU and `qemu-img` must be made available before any authorized ISO/installed-VM acceptance work. Preserve the listed runtime dirty paths and do not infer application readiness from source research.
