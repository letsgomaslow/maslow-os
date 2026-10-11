# Free Cloud AI optional program

Approved plan summary, 2026-10-11. This Git-backed program directory is the durable execution record. The development index remains the entry point; this plan does not authorize changes to the Craft optional-apps program. The prior FreeLLMAPI research checkout is an input to inspect; it was not a native package or live acceptance. Current exact baselines and preserved state are recorded in `tasks.json`.

## Outcome and fixed scope

Deliver a narrowly scoped, optional cloud-AI feature for existing Maslow OS users. Groq is the only provider and `gpt-oss-120b` plus `gpt-oss-20b` are the only permitted models. The user may submit typed questions and drafts. Creating a Markdown file requires a separate, explicit user action. Account access is limited to exact accounts selected by the user and is read-only. Reuse existing Voice; do not add a new voice route or alter consumer-agent configurations. The optional backend may use the private Node 22.23.3 `maslow-free-ai` package embedding FreeLLMAPI `65ec96df`. It must remain lazy and separate from base installation and the ISO.

The program covers the installed runtime, an optional fixed signed bundle, Hub setup/Work, a separately accepted Connect integration, recovery, guest and Lenovo validation, physical audio, and a live account. It does not authorize broad agent automation, general filesystem access, account writes, dynamic provider/model choice, package publication, product merges, or public promotion. Signing/publication and product-branch merges remain operator actions after review.

## Records and operating rules

| Record | Purpose |
| --- | --- |
| `tasks.json` | Dependency graph, phases, exact repository baselines, ownership, status, evidence, blockers and next actions |
| `tasks/<task-id>.md` | Scope, acceptance criteria, attempt history and evidence handoff for each task |
| `candidate.json` | Candidate inputs, required gates, passed gates and readiness; remains `not-ready` until all gates are directly evidenced |
| `evidence/` | Small sanitized evidence summaries; credentials, raw private logs and large artifacts stay outside Git |
| Dated handoff | Accepted checkpoints, exact commands/revisions, limitations and next runnable action |

At session start read applicable `AGENTS.md`, the development index and this program, then inspect the ledger, Git status, recent commits, branches and worktrees in every involved repository. Reconcile progress against files and artifacts before dispatch. Preserve existing edits. The manager is standard-library development tooling for explicit validation, status, claims and resume packets; it is not a scheduler. Never reclaim a task based only on age. Record actual model routing and unavailable checks honestly.

Only file-backed evidence supports completion. A mock, unit fixture, cached-only response, successful package build, or successful setup screen cannot establish live provider, live account, revocation, physical audio, or machine acceptance. Every dispatch checks the software-owned provider/model policy, regardless of whether model catalogs were fetched live or loaded from cache. Malformed policy fails closed. Invalid or unavailable catalog updates retain prior verified state; catalog availability cannot expand or replace Maslow policy. Never log or expose secrets.

## Phases and exit gates

| Phase | Work | Exit gate |
| --- | --- | --- |
| 0 | Persist plan, inventory repositories, inspect existing optional package and reconcile preserved changes | All boundaries, baselines, dependencies and blockers are recorded; ledger validates; no results are inferred |
| 1 | Groq/model dispatch policy; Secret Service and lazy lifecycle; managed Hermes tools and request contract | Every dispatch enforces provider/model policy; fetched and cached catalog paths are covered; encryption material remains in Secret Service and provider keys remain in upstream encrypted SQLite; owned-port and process lifecycle failures recover safely; Hermes exposes only managed tools; idempotency contract is enforced |
| 2 | Fixed signed optional bundle and Hub setup/Work experience | Exact reviewed bundle is optional, signed and fixed; lifecycle/status are truthful; no base package or ISO inclusion |
| 3 | Connect account boundary | Only explicitly selected exact accounts are available read-only; scope is checked; revoke/disconnect immediately removes access and invalidates stale sessions |
| 4 | Complete database/key/package recovery | Database backup/restore and corruption, key loss/rotation, package install/upgrade/removal/rollback and interrupted-operation recovery pass without losing user data or widening access |
| 5 | Clean guest and Lenovo acceptance, live account and physical audio | End-to-end user flow, live authorized account, account revocation, existing Voice, microphone/speaker path and recovery are directly observed in both environments |
| 6 | Independent review and exact candidate release record | Exact inputs and artifacts pass all gates; unresolved review findings block readiness; release instructions keep signing/publication/merges as operator actions |

## Interfaces and acceptance detail

The runtime accepts typed questions and drafts. It writes no files implicitly. A Markdown create operation requires an explicit user request with a bounded destination and saved-file verification. The Groq boundary permits only the two named models, allows only the approved same-provider fallback, and rechecks policy at dispatch even when catalogs are cached.

Encryption material lives in Secret Service; provider credentials remain in upstream encrypted SQLite, with lazy setup and use of the private `maslow-free-ai` Node 22.23.3 backend package only when required. Startup binds only its owned port and handles collision, process death, timeout, partial installation and shutdown without leaving an orphan service or exposing the key. Hermes receives only managed tools and an explicit contract containing `request_id`, `original`, `workspace`, `execution_connection`, `policy`, `files`, and `accounts`. Replays are idempotent; mismatched or unauthorized requests fail closed.

The Hub offers a fixed signed optional bundle and explicit Setup and Work states. It does not select arbitrary providers, models, packages, tools or accounts. Connect must be independently accepted: it grants only selected exact accounts with read-only scope, checks account identity and scope before each operation, and revocation/disconnect removes the capability. A Craft Connect revision under review is not accepted Free Cloud AI evidence.

Recovery acceptance includes database restore and corrupt/missing DB behavior; lost, rotated or unavailable keys; missing, partial, upgraded, removed or rolled-back packages; interrupted requests; and retry behavior. Preserve user data and never restore stale credentials or account access silently. Final acceptance uses a clean guest and the Lenovo with a live authorized account and physical microphone/speaker observation through existing Voice. Mocks and prior reports cannot satisfy these gates.

## Resume instruction

> Read the applicable repository instructions and development index, then `docs/programs/free-cloud-ai/README.md`, `tasks.json`, and the relevant task charter. Reconcile status, commits, worktrees, package artifacts and evidence. Resume dependency-ready work, preserve existing changes, and record exact results. Keep `candidate.json` not-ready until every required gate is directly evidenced.
