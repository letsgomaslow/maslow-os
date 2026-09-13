# Maslow AI-OS development: start here

Updated 2026-09-13. This is the current workstream index, not a stable-release announcement. Update this file at each meaningful checkpoint; keep detailed evidence in dated handoffs rather than expanding AGENTS.md into a second backlog.

Voice implementation: [Maslow Voice implementation and acceptance](handoffs/2026-09-13-maslow-voice-implementation.md) records the separate `codex/maslow-voice` runtime, Hub and package worktrees and remaining live-provider/hardware gates. The [Voice Hub 0.3.0 OTA delivery handoff](handoffs/2026-09-13-maslow-voice-ota-delivery.md) records completed installed checks, operator signing and public staging sequence 4, anonymously verified September 13. Source branches remain local and unmerged; the signed delivery artifact is published. Resume Voice release work there.

Current priority: on Lenovo, use Hub Updates to install 0.3.0, then Voice → Install Voice and configure the chosen cloud provider. The Mac signing and publication steps are complete. Public distribution commit `bfd869fbb4da6776abe24fff58de01fe3afe20b7` and anonymous verification establish delivery, while Lenovo installation and live audio remain open. Follow the [Voice OTA handoff](handoffs/2026-09-13-maslow-voice-ota-delivery.md), then resume the separate [support-readiness closeout](handoffs/2026-09-12-support-readiness-closeout.md). Remote support infrastructure remains proposed.

## Resume in a new context

1. Read this file and [the latest support-readiness closeout](handoffs/2026-09-12-support-readiness-closeout.md), then [recovery release evidence](handoffs/2026-09-11-hub-recovery.md). Use older linked handoffs for provenance, not current signing or device instructions.
2. Run `git status --short --branch`, `git log -5 --oneline`, and `git worktree list` in each repository you will touch. The saved runtime `main` checkout is not the Hub implementation checkout. Do not repeat implementation just because main lacks Hub.
3. Select one ready backlog item below; identify its owner repository, acceptance criteria, delivery path, and dependencies before editing. Read that repository's AGENTS.md and matching task guide.
4. Preserve unrelated changes and accepted images. No automatic push, branch merge, release publication, key provisioning, or disk erase follows from a documentation update.
5. End with focused checks, exact source commits, evidence locations, unresolved risks, and the next executable step. A fresh conversation must not need chat history to distinguish completed work from a test fixture.

## Repository and branch map

| Repository | Ownership | Current Hub work | Product branch |
| --- | --- | --- | --- |
| `letsgomaslow/maslow-os` | Runtime, discovery, defaults, first login, branding | `codex/maslow-hub` | `main` |
| `letsgomaslow/maslow-os-pkgs` | Package recipes, ownership, hooks | `codex/maslow-hub` | `maslow` |
| `letsgomaslow/maslow-os-iso` | Installer, offline mirror, installed-guest harness | `codex/maslow-hub` | `maslow` |
| `letsgomaslow/maslow-hub` | Native Hub UI, onboarding presentation, catalog, helper/updater | `main`; newer-release fixture is in a separate local clone | `main` |

Local discovery hint: the coordinated worktrees are under `/Users/r.david/.codex/worktrees/43ab/`, with directories `Maslow OS - Linux`, `Maslow OS - Packages`, `Maslow OS - ISO`, and `maslow-hub`. Use Git to rediscover paths; do not make scripts depend on this machine-specific location. These paths and local commits are not off-machine backups. The Hub remote was created private; the work has not been published. Inspect remote state before any future integration or push.

The separate test clone is `hub-evidence/source-next` under that same local root, branch `codex/fresh-update-fixture`, commit `30e1db3`; it is not a branch in the main Hub checkout. Do not promote it or treat a missing fixture branch in the main checkout as lost production work.

## Current baseline and evidence limits

- Internal ISO: `maslow-os-2026.09.08-x86_64-hub-0.1.3-sizing-local-internal.iso`, 6,485,413,888 bytes; SHA-256 `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`.
- Built runtime `dca4d9c824f958719c54c1ac09db0ffd82e89b68` includes approved branding `b69f785f` through `960bb961`, plus responsive screensaver sizing. Runtime package is `4.0.0.r2077.gdca4d9c-1`; unchanged settings intentionally remain `4.0.0.r2075.g960bb96-1`.
- Hub built source `9e0376567144bdbcf72f45203fbfeb457d381974`, version `0.1.3`, helper interface `1`; package recipes `c8506a142a37389f39006676e37ab89799f4e125`; ISO builder `ae6bf9f9a5ed38057e35479125741e3d9175bab3`. Full submodule, archive, and acceptance revisions are in the evidence handoff. Later documentation commits do not change built artifacts.
- Final corrected ISO: artifact inspection and all 31 fresh-install checks passed in headless QEMU/TCG. Screensaver fits at 1280×800; wide preview retains 18 points. USB full-image readback matched the checksum and safe eject completed.
- Independent graphical `0.1.3 → 0.1.4 → 0.1.3` and six preservation hashes passed on the preliminary fresh-installed ISO with the exact unchanged Hub archive, not on the corrected ISO. `0.1.4` is a visibly newer test fixture, not a release to promote. Terminal recovery also passed with the shell stopped in the migration rehearsal.
- The user subsequently confirmed “Lenovo installation reached desktop.” Fresh installation reaching the desktop is passed as tester-reported hardware evidence. Reboot, onboarding, Bitwarden, authentication, and device update/rollback remain separate unverified checks.
- On 2026-09-09 the user additionally reported successful everyday use of the installed Lenovo. This strengthens reported usability evidence, not itemized native update/recovery or authentication acceptance.
- The accepted ISO requires one-time client trust enrollment; the Lenovo has already completed it and visibly runs 0.2.1. Signed staging sequence 3 retains 0.2.0 and exact 0.1.3 recovery packages. Stable/alpha promotion, Lenovo rollback, installer redistribution and itemized native acceptance remain separate gates. See the latest closeout before older checkpoints.

## Feature state

The table below describes the accepted ISO installation baseline, not the later 0.2.1 OTA feature state. Current release and support gaps are in the [latest closeout](handoffs/2026-09-12-support-readiness-closeout.md). The ISO remains unchanged.

| Area | Current behavior | Not yet established |
| --- | --- | --- |
| Hub | Setup, Connections, Featured, Updates inside existing Quickshell; package-owned extension | Production release delivery |
| Setup | Supported tool actions, preserved progress, optional skippable Observability | New observability service or automatic provider authorization |
| Connections | Separate Connect portal handoff and bridge availability | All-provider authorization or universal MCP acceptance |
| Featured | Offline/signed data-only catalog and explicit web-app management | Full marketplace installation and arbitrary harness installers |
| Defaults | No OBS, Kdenlive, Moonlight, or bundled web-app launchers on fresh installs | Removal from existing user homes, which is intentionally not performed |
| Infrastructure | Existing installed/optional policy preserved; ONCE and Ollama remain optional | Blanket installation of every infrastructure tool |
| Secrets | Bitwarden remains in the ISO and setup catalog | Isolation of personal secrets from unrestricted local AI agents |

Bitwarden installation is not an agent-security boundary. Do not give agents a personal vault unlock token, broad environment secrets, or unrestricted administrator access and claim the vault is hidden. Keep tests synthetic until a reviewed isolation boundary exists. Design a separate restricted execution environment and narrowly approved credential operations before promising agent-inaccessible secrets.

## Prioritized backlog

Lift estimates are relative engineering effort, not dates: XS = focused copy/checklist change; S = bounded feature or adapter; M = coordinated implementation with integration tests; L = security/platform work spanning several components. Dependencies and safety gates outrank cheap features. No row authorizes publication or account changes by itself.

| Order / ID | Deliverable and acceptance | Lift | Owner / delivery | Dependency |
| --- | --- | --- | --- | --- |
| P0 / A1 | Capture itemized Lenovo results: install, USB-detached reboot, Hub, Bitwarden lock/unlock with test data, fresh app install before OS update, web-app lifecycle, errors | XS engineering; user hardware time | Runtime docs; no rebuild | User observations; no secrets in evidence |
| Maintenance / A2 | Signed staging operational; renew metadata before September 24, 2026 expiry; encrypted key recovery remains operator-managed | S; operator signature | Public distribution | Preserve immutable packages and trust; explicit promotion |
| P0 / A3 | Staging and Lenovo 0.2.1 arrival established; complete native rollback/recovery and feature acceptance before alpha | M remaining | Hub + packages | No repeated bootstrap; distinguish public verification from native acceptance |
| P0 / R1 | Define safe support schema/consent, then durable timeline and preview/send/report-reference workflow | S design; M implementation | Hub + separately approved private serverless intake | Read latest closeout; hosting, authentication, retention and cost controls need decisions |
| P0 / R2 | Reproduce denied/stale Docker access, restart/resume and backend failures; show one accurate next action and diagnose from a report | M | Hub + installed x86 testing | R1; real traces remain required; no unrestricted remote shell |
| P0 / A4 | Resolve Chrome redistribution before external images; if replacement needed, preserve a usable default browser and test fresh installs | S investigation; implementation TBD | Packages + ISO | Distribution approval; do not guess legal clearance |
| P0 / A5 | Review and integrate coordinated branches, back up approved source remotely, record exact release inputs and complete Lenovo update/rollback using real channel | S–M | All repositories | A1–A4; source push/merge approval; no test-fixture promotion |
| P1 / Q1 | Fix installer tip that still advertises Kdenlive as a default; verify wording matches optional availability | XS | ISO source; next planned media build | Do not rebuild accepted media solely for this wording |
| P1 / Q2 | Collect onboarding feedback; improve loading/error/retry/skip copy and visible readiness without resetting progress | S per slice | Hub package release | Keep installation, configuration, authentication, permission consent distinct |
| P1 / Q3 | Add clear Bitwarden setup/locking guidance and document personal-vault versus agent credentials | S | Hub/docs | No claim of isolation; test with synthetic credentials |
| P1 / Q4 | Make cache/resume preflight reusable: verify cache layout, self-contained Git snapshot, exact package inputs, and only rebuild changed packages | S–M | ISO tooling | Preserve signature checks and old images; use existing evidence scripts as references |
| P1 / Q5 | Reproduce intermittent Featured status-read warning and fix root cause if found; retain malformed-then-valid regression | S investigation, fix TBD | Hub | Warning recovery fixed in 0.1.3; original cause remains unconfirmed |
| P0 / F1 | Complete local Langfuse adapter: candidate code/package exists; real traces, resource measurements, bounded logs/resource presentation, startup and recovery acceptance remain | M | Hub package; optional install | A3; native x86 evidence; no backend in ISO by default |
| P2 / F2 | Adapt Connect to the approved local/serverless boundary, then improve detection and prove one provider with authorization/revocation | M–L; S architecture slice | Separate Connect, then Hub | Follow Connect's `docs/serverless-local-roadmap.md`; Vercel preferred, no VPS; durable state/policy decision required; not an OTA prerequisite |
| P2 / F3 | Curate more data-only Featured entries with evidence-based Tested/Experimental/Coming soon labels | S | Signed catalog | A3; no executable catalog content |
| P2 / S1 | Threat-model agent/secret separation; prototype restricted agents and user-approved credential operations, then adversarially test filesystem, clipboard, screen, sockets, and privilege boundaries | L overall; S design slice can start early | Runtime + Hub/Connect | Security review before handling real personal credentials; do not rely on prompt instructions |
| P3 / F4 | One tested Paperclip/Hermes harness adapter, including compatibility, permissions, update and removal | M–L | Hub | Keep Coming soon until end-to-end proof; separate from full marketplace |
| P3 / F5 | Full marketplace installer, universal memory, model routing, broad harness support | L | Separate scoped workstreams | Deferred; avoid expanding foundation work |

Current checkpoint: Hub 0.3.0 Voice preview is signed, published and anonymously verified on staging sequence 4. Installed test-channel update, rollback, corrected reapply, preserved state, post-emulator-crash recovery, inspected final UI and cleanup passed as detailed in the Voice handoff. Lenovo's latest observed version remains 0.2.1; the next action is its Hub update and explicit Voice installation. A3 physical Lenovo recovery and F1 Observability backend/trace acceptance remain open; Voice live-provider/audio acceptance is a separate open gate. R1/R2 remain recommendations, and security design S1 still blocks any promise of agent-hidden secrets.

For A2/A3, follow the [internet OTA workflow and payload options](ota-update-workflow.md), as superseded by the approved [local Langfuse implementation milestone](handoffs/2026-09-09-hub-ota-observability.md). The payload is a working optional local backend plus guidance, not just a Coming soon screen. Prove `0.1.3 → B → rollback → B → C` on installed systems. Connect's serverless adaptation and OS package updates remain independent. No ISO rebuild is needed; release promotion remains explicit.

## What worked, what failed, what to reuse

| Observation | Lesson / future action |
| --- | --- |
| A package installed but Quickshell could reuse old QML | Keep version-specific QML paths; verify visible new UI and unchanged shell PID, not pacman success alone. |
| Closing Hub could kill its update child | Keep the update operation alive until completion; reload only after transaction completion. |
| Terminal Polkit failed while GUI authorization worked | Use terminal sudo versus GUI Polkit through the same narrow verified installer; retain recovery independent of Quickshell. |
| Managed timer symlink hit overly broad archive rejection | Permit only the reviewed package-layout case; preserve malicious-link tests. |
| One Featured status parse warning persisted | A successful refresh now clears it; fixture proof is not a reproduced root-cause fix. |
| Initial frames were black/incomplete; animation and first-login prompt obscured captures | Wait for settled real rendering, retain the accepted frame, distinguish startup/transition frames from regressions. Do not accept screenshots without inspecting them. |
| Approved 100-column banner clipped at 1280×800 | Test logical monitor sizes and UTF-8 display columns; keep artwork intact and cap wide-screen font size. |
| Mirrors timed out and a nested cache path prevented reuse | Validate cache layout before expensive work; resume exact archives and keep normal checksum/signature verification. |
| Container snapshot referenced host-only Git alternates | Create self-contained source snapshots and verify their commit resolution inside the builder before rebuilding. |
| macOS administrator approval did not allow raw USB access from the app | It failed before writing. Normal authenticated Terminal succeeded; revalidate target, verify full ISO-length readback, eject. Never hardcode a historical disk number or ask for passwords in chat. |
| Full ISO/TCG testing was slow | Iterate UI in Docker + headless Weston + real Quickshell/software rendering; use installed overlays for app changes; build media only at baseline/integration checkpoints. No UTM. |
| Broad cross-task reads and minute-by-minute progress create overhead | Delegate one bounded task per worker, at most two workers; return compact findings. Use cursor-based status waits, do not reread full task transcripts or narrate unchanged state. |

## Verification and session closeout

Current publication record: signed staging sequence 4 / catalog sequence 1, distribution `bfd869fbb4da6776abe24fff58de01fe3afe20b7`, anonymously verified September 13 at 19:16:59 UTC. Immutable versions 0.1.3, 0.2.0, 0.2.1 and 0.3.0 are available; metadata expires September 24, 2026 at 23:56:41 UTC. Mac signing and publication are complete. Lenovo's supplied photo still establishes only 0.2.1 arrival, so confirm its 0.3.0 update and Voice behavior next. Follow the [Voice OTA handoff](handoffs/2026-09-13-maslow-voice-ota-delivery.md); existing trust enrollment is reused.

### Historical checkpoints, not instructions to repeat

Publication checkpoint: user approved publication, but GitHub rejected bare checksum tags with HTTP 422. Nothing is public except the prior scaffold; one failed unpublished baseline draft remains. Release-only fix `fe4b9b8` uses `sha256-<digest>` tags and passes 73 tests plus UI checks. Exact package bytes/signatures are unchanged. A prepared sequence-2 manifest needs one operator signature via `hub-evidence/ota-ui-020/sign-staging-url-fix.sh`; then continue already-authorized promotion. See the UI staging handoff's publication-attempt section. Do not repeat the original signing script, rebuild packages, or ask for publication approval again solely for this naming fix.

2026-09-10 UI staging checkpoint: user approved a narrowly scoped experiential OTA test, separating experimental observability maturity from mandatory update safety. Hub `6ea55de` restores guided setup and a returning-user overview; 71 Python tests, guided UI contract checks, inspected real Quickshell renders, package ownership, and installed-guest setup/launcher preservation passed. New unsigned 0.2.0 package SHA-256 `498dc7883ecd8bd11ae3539d549554b1dd423b41d02b12facc83a43b388dc992` supersedes the earlier unpromoted candidate for this test. No ISO rebuild or Lenovo change. QMP output remained inactive, not installed visual proof. Operator signing script is ready; next is local signing, exact-artifact publication review, anonymous verification, then Lenovo enrollment/OTA feedback. Read the new UI staging handoff before acting on older broader release gates.

Installed smoke limitation: final shell IPC also timed out, so plugin reload is unconfirmed despite successful package installation and unchanged saved files. See the staging handoff before claiming installed visual/update acceptance.

2026-09-10 signing checkpoint: operator-created encrypted key and public fingerprint are recorded in the current OTA handoff; separate recovery backup is operator-reported, not restore-tested. Exact baseline/candidate package hashes match and Hub's 69 Python tests plus release checks passed again. No release or channel was published and no Lenovo trust was changed. Native observability validation and candidate acceptance, not key creation, are the next release blockers. Checkpoint documentation is local and uncommitted; accepted artifact revisions remain unchanged.

2026-09-09 implementation checkpoint: Hub `b28d515`, package recipes `e4fab06`, public distribution `7e38da2`; 69 Python tests, UI contract, package checks, inspected native previews, and installed package/preflight rejection passed. No production release was published. Backend startup failed under Apple amd64 emulation; real traces, hardware measurements, signed OTA sequence, release C, and specified presentation gaps remain open. See the current handoff for exact package hash and evidence. The accepted ISO is unchanged.

2026-09-09 checkpoint: documented A2/A3 internet delivery workflow, candidate payloads, and the separate Connect local/serverless roadmap. Existing relative-link targets and repository identity were checked; documentation whitespace checks passed. No code, deployment, trust, accepted artifact, or device state changed. Runtime/graphical tests were not rerun for documentation-only edits. Lesson: local MCP transport is not a local-only backend, and a visible feature is not proof of an operational internet channel. Next decision: artifact endpoint and signing-key custody, then secure installed-client bootstrap. Find the scoped documentation commits in each repository's Git history; accepted build revisions above remain unchanged.

- Documentation-only work: validate relative links, referenced commits/paths, `git diff --check`, and staged scope. Do not rebuild an ISO or rerun unchanged graphical/security suites for documentation edits.
- Hub changes: from Hub root, run `python3 -m unittest discover -s tests -p 'test_*.py'` and `node tests/ui-contract-test.mjs`; consult its security/recovery docs before update changes.
- Runtime changes: use `docs/testing.md` and matching task guides; focused tests include `test/shell.d/maslow-hub-routing-test.sh`, `test/shell.d/maslow-slim-defaults-test.sh`, and `test/shell.d/launch-screensaver-sizing-test.sh`. Run Linux-dependent checks in the supported Linux harness, not by weakening them for macOS.
- Package/ISO changes: follow their own AGENTS.md; ownership and local-package checks precede image assembly. Graphical installed-system proof uses ISO headless QEMU/TCG, unattended CIDATA, SSH, and QMP capture/OCR. Hardware proof uses Lenovo USB.
- Keep precise evidence levels: source test, rendered UI, exact package, exact ISO, USB readback, tester-reported hardware, observed hardware, production delivery. A skipped test or fixture is not device acceptance.
- Each session closeout records: task ID/status, files/repositories, commits, tests with pass/fail/skip, artifacts with hashes, failure/cause/fix, remaining gates, and the next command or user decision. Keep keys, provider data, private endpoints, large logs, screenshots, and ISOs out of source commits.
