# Maslow Craft optional apps program

Approved execution plan, 2026-10-11. This Git-backed directory is authoritative; chat summaries and historical worker IDs are not evidence. [Development index](../../maslow-development.md) remains the entry point. The prior [56-repository research](../../handoffs/2026-10-11-storytold-app-review.md) retains the other 44 repositories' dispositions; they are not implementation targets.

## Outcome and limits

Evaluate all 12 Craft desktop applications. Prepare release-ready experimental candidates only for apps that pass their declared gates. Record concrete deferrals/exclusions and reconsideration conditions for the others. Start PdfCraft and PhotoCraft, then VectorCraft, WordCraft, GridCraft, DeckCraft, LightCraft, EffectCraft, FilmCraft, DesignCraft, CADCraft and SoundCraft. Completion requires all 12 evaluations and every included candidate's gates; package builds alone do not establish integration.

The standard offering requires verified project isolation and headless saved-file workflows. Live-window automation is a separate future program. Target existing x86_64 Maslow OS/Hyprland only. Keep applications and Connect optional, out of the base package list and ISO payload. Finish with exact verified candidate packages and release instructions. Production signing, publication, product-branch merges and public promotion remain separate operator actions. Do not change installed consumer-agent models/accounts to match development routing. Small required upstream patches must be pinned, reviewable and regression-tested; substantial upstream product development is outside scope.

Context loss is a recovery event. Account, machine, platform concurrency and physical-test limitations remain real gates. Never infer successful tests from an earlier conversation.

## Records and state

| Record | Purpose |
| --- | --- |
| `tasks.json` | Coordinator-owned ledger and dependency graph |
| `tasks/<task-id>.md` | Objective, permitted files, dependencies, acceptance, attempt history, findings, changes, tests, handoff |
| `apps/<app-id>.md` | Package, compatibility, confinement, workflow and disposition evidence |
| `candidate.json` | Exact source revisions, package versions, hashes, accepted capabilities and invalidation rules |
| `evidence/` | Small sanitized evidence summaries; raw logs, corpora, binaries and VM images stay outside Git |
| Dated runtime handoff | Accepted checkpoints, exact inputs, blockers and next runnable action |

Tasks move queued → active → implementation-complete → verified → integrated; blocked includes a specific blocker and next action. App dispositions are evaluating, candidate, deferred or excluded. Release readiness applies to one manifest and its evidence, never permanently to an application name. Each task records owner, worker/session, actual model, attempt, checkpoint, baseline, branch/worktree, implementation/integration commits, tests/evidence/artifact hashes and next action. Unavailable measurements/models are recorded honestly.

The Python standard-library `manage.py` is development tooling, not an OS service or autonomous scheduler. It validates IDs, dependencies/cycles, ownership conflicts, missing evidence and interrupted claims; it provides status, explicit claims and a resume packet. Never reclaim merely because a timestamp is old. Confirm or interrupt live workers; in new sessions reconcile worktree/report/commits/artifacts first. Missing artifacts must be rebuilt or marked unavailable. Changed inputs invalidate affected evidence.

## Operating procedure

At start read applicable AGENTS.md, the development index, this file, ledger and latest handoff. Inspect Git status, recent commits, branches and worktrees. Reconcile recorded progress with files, commits and artifacts. Recover interrupted work before replacement dispatch. Select dependency-ready tasks and persist charters first.

The coordinator owns the ledger, shared interfaces, integration branches, phase gates and final verification. At each accepted task, phase transition, material blocker, transfer and session close: update task/app records and exact evidence; commit only scoped program and accepted implementation changes; update the concise index/checkpoint; record next runnable task/prerequisites. Preserve user changes and partial work. No reset/delete of disappeared workers' work.

Use one coordinator and at most two independent workers. Give implementers separate worktrees and disjoint file ownership. Workers can update only their assigned central task report. Keep ledger and shared-file integration with the coordinator. Messages coordinate immediately; persist decisions before dependent work. Worker success means implementation-complete; coordinator reviews diff/evidence before verification/integration. Reviewers report findings without changing reviewed code. Package builds and physical audio tests run sequentially on this host. Diagnose a failure and revise before one retry; an equivalent repeated failure requires takeover, stronger review or a concrete blocker while independent work continues.

| Work | Preferred actual worker model | Reasoning |
| --- | --- | --- |
| Bounded inventory/docs/evidence | gpt-6-luna | medium |
| Ordinary implementation/packages/debugging | gpt-6.1-sol | medium |
| Lifecycle races/migrations/difficult code | gpt-6.1-sol | high |
| Confinement/trust/final review | gpt-6-astra | high |

Use gpt-6-sol when Sol 6.1 is unavailable, or independent high-reasoning Sol review if Astra is unavailable. Check the execution surface; record actual routing/limitations, never invented savings. Terra is unavailable. Explicit subagent selection is supported here; account/client execution can still fail. [Official model routing reference](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Fixed product interfaces

### Packages

Create native `maslow-connect` before claiming installed Connect workflow. Each accepted app package contains GUI/CLI, stable executable paths, desktop entry/icons/notices, pinned version/verified hash, actual Arch dependencies and ownership. Prefer reviewed release archive. If contents/ABI fail, build the same tag with its lockfile; if both fail, defer rather than silently using main. Pacman owns updates; upstream self-update must not replace package-owned files. Bubblewrap is an optional Connect package dependency, not a newly assumed base-image dependency.

### Hub

Keep signed featured-catalog schema unchanged. All actions are fixed local code. Add bounded `apps` list/inspect/install/open/connect/disconnect/remove/operation-status actions using existing JSON envelope. Only accepted local capabilities enable actions; all remain experimental. Require explicit existing project/output folders and selected agents.

Reserve operation ID before opening terminal. Explicit stages cover terminal handoff, installation, verification, completion, failure and interruption. A launched terminal is not installation success. Verify registered package/version/executable ownership/CLI after install. Serialize mutations, reconcile interruption on reopen and prevent duplicate-click jobs. Agent edits run as user. Disconnect only Maslow-owned entries before removal; active managed sessions or unwiring failure block removal. Fixed package removal has no broad dependency sweep; preserve preferences/documents.

### Connect confinement

Fixed profile builders and launcher expose bounded operations equivalent to `craft connect APP --project DIR --output DIR --agents IDS`, `craft status APP`, `craft disconnect APP` and an internal fixed-profile launch. Require explicit roots and agents; generic all-installed-agent default does not apply. One managed project profile per app in v1; change project by disconnect/reconnect and refuse replacement with active sessions.

Sandbox gives read-only approved project; writes only selected output subtree and private app state/temp; read-only reviewed system runtime/fonts/app resources. No general home, account configuration, network, host bus, desktop/audio sockets or inherited credential environment. Private process/IPC/network namespaces, minimal devices, closed unrelated descriptors. Fixed executable/args; caller cannot add commands/mounts. Fail closed, never unrestricted fallback. Preserve canonical host artifact paths. Native root flags supplement OS boundary. Reject unsafe roots/overlaps; test symlinks and replacement. Private state is user-owned per app/project, persists without provider credentials; serialize conflicting sessions. GUI launches remain independent user apps. The sandbox claim does not extend to those windows or the agent. Explain selected project files can be returned through MCP to the agent/provider: read-only does not guarantee confidentiality.

Strengthen registry serialization, verified selected-agent unwiring, save-failure recovery, partial wiring/unwiring and durable retry/reconciliation. Retain task identity, approvals, cancellation and artifact provenance. Five-second graceful stop precedes termination of the owned process group; verify parent death, hangs, exhaustion and cleanup.

### Agents and Voice

Required spoken path: Voice → configured visible Codex → confined Craft MCP → saved artifact. Verify direct workflows in Codex, Claude Code and Hermes. Test remaining existing adapters' configuration/launcher paths before advertising them. Preserve strict cloud Claude SDK configuration; do not import arbitrary saved servers. Extra Voice routes need separate evidence. Announce completion only after expected file exists and relevant contents are checked. Actual speech intent, route, output/content, cancellation, denied-action recovery and audible result must be observed; synthetic checks cannot pass physical Voice gates.

## Phase gates

| Phase | Work | Exit gate |
| --- | --- | --- |
| 0 | Persist plan/ledger/apps/charters/resume procedure, inventory worktrees, locate/obtain ISO harness; Luna validates coverage | Durable records committed; all 12 apps, baselines, preserved changes, prerequisites and graph recorded |
| 1 | Sol A packages Connect and implements fixed profiles/sandbox/lifecycle; Sol B packages PdfCraft/PhotoCraft; Astra reviews boundary | Three packages build, ownership/deps verified, positive/negative isolation pass, packaged launch independent of dev paths |
| 2 | Fixed Hub actions, tracking, roots/agents, accessible cards; independent contract/lifecycle coverage | Honest install/connect/remove, interruption/duplicate recovery, real Quickshell inspected |
| 3 | Exact two-app candidates; sequential package/format/agent tests and physical audio | Fresh-install GUI/confined MCP/selected agents/Voice/upgrade/remove/reinstall/fidelity pass |
| 4 | VectorCraft, WordCraft/GridCraft, DeckCraft | Candidate or explicit evidenced deferral/exclusion for each |
| 5 | LightCraft/EffectCraft, FilmCraft, DesignCraft/CADCraft/SoundCraft | All remaining dispositions; defer v1 requirements for network/unsafe access/unsupported sockets/substantial repair |
| 6 | Exact manifest/release checklist; independent Astra review; exact-revision ISO/fresh VM | Traceable packages/capabilities, all required gates, operator release instructions prepared without execution |

Separate each app's package, GUI/CLI, confinement, MCP, Voice and disposition tasks. Dependencies prevent package success from being mistaken for full app readiness. Shared phase tasks collect gates; later phases cannot silently bypass pilot acceptance.

## Verification and reporting

Records: duplicate/missing/cyclic dependency detection, conflicting ownership, interrupted claims, completion without evidence, fresh-session recovery. Packages: clean builds/checksums/contents/licenses/deps/overlap, install/upgrade/remove/reinstall and offline launch. Hub: owning Python suite/UI contract, real Quickshell, terminal failure/interruption/repeated clicks. Connect: owning typecheck/build/tests, packaged MCP handshake, selected-agent wiring/verified unwiring.

Isolation tests: authorized reads/exports; outside-root/traversal/symlink/path-replacement denial; inherited secrets/network/sockets/subprocess escapes. Lifecycle: disconnect/cancel/parent death/hangs/exhaustion/cleanup. Installed product: fresh optional install before first OS update, disposable VM and required Lenovo checks. Owning repository checks remain required; repeat unchanged passing checks only for new changes/failures/unresolved concerns.

App fidelity: PDF/image save/reopen, SVG render, DOCX/XLSX/PPTX round trips and known-answer formulas, representative RAW, video/audio exports, CAD units/dimensions and publishing layout. Report current phase/ready tasks, integrated versus planned, app dispositions/gates, blockers by implementation/upstream/environment/operator, exact candidate inputs/artifacts and actual models/available usage. Candidate manifests must stay unready while gates are missing.

## Resume instruction

> Read the applicable AGENTS.md instructions, `docs/maslow-development.md`, and `docs/programs/craft-optional-apps/README.md`. Reconcile the task ledger and latest handoff against Git and artifacts. Resume dependency-ready work with at most two independent workers, preserve existing changes, and checkpoint accepted results.

An explicitly identified Codex session may also be resumed, but these records remain authoritative. [Official session resume reference](https://learn.chatgpt.com/docs/non-interactive-mode).
