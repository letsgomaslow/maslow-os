# Maslow Voice: product direction, MVP and lessons

Updated 2026-09-20. This is the product and learning reference for the Voice MVP. The [development index](maslow-development.md) owns current status; the [implementation handoff](handoffs/2026-09-19-voice-mvp.md) and [installed evidence](handoffs/2026-09-19-voice-noforms.md) retain exact revisions, failures, package hashes and local evidence paths. Merging source is not completion of physical acceptance or publication of a stable package channel.

## The bigger goal

Maslow should let a person describe an outcome, discuss it, delegate the work and remain in control. Voice is the primary interaction, with typing and visible applications available whenever they are more useful. The OS integration should remove bookkeeping from the user's path: choosing tools, preparing workspaces, maintaining task history, tracking execution and bringing back inspectable results.

The intended role is an executive assistant or chief of staff for a power user, not a relationship simulation. The product should accommodate rapid topic changes and unfinished thoughts, including the attention-management needs the user described, without making medical claims. Thinking aloud, exploring an idea, deciding to act and granting permission are different events. A passing thought is not authorization to start work.

Maslow Hub can provide shared setup, tool readiness and connections; Voice can be the conversational entry point; a daemon-owned task boundary can coordinate agent execution. Over time, shared project context, decisions and results can reduce repeated setup across tools. This does not establish that arbitrary agents share compatible memory, that any subscription pays for every provider, or that OS window control grants semantic control of every app.

The longer-term opportunity includes user-controlled memory, organizing ideas into projects and tasks, and preparing research under explicit standing scope and budgets. None of those ambitions justifies silently launching work, spending money, installing software or contacting others. Proactive work needs an inspectable mandate, cost limits, cancellation and a clear account of why it ran.

## What this MVP is supposed to prove

Prove one complete journey on Lenovo: “Build a simple app using Codex” → automatic setup → visible work → continued conversation → correction → inspectable result. Opening an application must also work independently of creating a project. Success means less effort than opening a terminal and typing the request yourself.

The deliberately narrow choices are Gemini conversation, one active Codex job, existing task storage and execution adapters, and the existing Quickshell Tasks view. There is no new orchestration framework, added dependency, Hub redesign or ISO rebuild. Other providers and agents remain available; expose only capabilities their adapters implement.

Forms are not the default strategy. Ordinary conversation and delegation must not require project names, folder selection, descriptions or technical implementation choices. Maslow prepares a brief and routine defaults from the user's words. Advanced overrides can remain available without becoming an intake gate. Ask a concise question only when the answer materially changes the outcome, resolves real ambiguity or supplies a required permission.

The Orb stays a simple, stable entry point. Microphone/conversation state and background work are separate: a completed job must not look perpetually busy, and ending speech must not cancel work. A full visual redesign and playback-driven animation are outside this MVP.

## User journey and ownership

| Step | What the person does | What Maslow owns |
| --- | --- | --- |
| Connect | Complete supported provider and agent setup | Show conversation readiness separately from agent installation, authentication and permissions; retain supported billing routes |
| Converse | Click the Orb and talk, or type a message | Keep ordinary discussion free of task/project requirements; do not turn brainstorming into execution |
| Open an app | Say “Open Codex,” Browser, Files, Hub or Terminal | Use bounded registered targets, observe the window and refocus it on repeated requests; report setup or launch failure honestly |
| Delegate | Say “Build a simple calculator app using Codex” | Preserve original words, prepare the brief, resolve/create a workspace, bind it to a durable task record, return a receipt promptly and show actual job activity |
| Stay involved | Discuss another topic, ask for progress or give a correction | Keep conversation available; route typed and spoken instructions through the same task-control path and exact running turn |
| Review a decision | Approve or deny a displayed request | Bind the answer to that exact task, child and pending request; never let the conversation model approve on the user's behalf |
| Stop or recover | Stop the displayed task, or Continue an interrupted/completed task | Cancel the correct job and approvals; preserve files/history; explicitly resume the saved Codex thread through a recorded attempt |
| Inspect the result | Read the report, open the folder or artifact | Check that a referenced file exists within the workspace; distinguish agent claims, Maslow checks and unverified behavior |

A standalone Codex terminal is a separate session. Opening it does not attach it to the delegated job. For this MVP, direct intervention in delegated work occurs in the Maslow task view. The UI must not imply terminal takeover that the adapter does not provide.

Workspace selection is deterministic: explicit existing selection, then the established conversation project, otherwise a readable collision-safe directory under `~/Projects/Maslow Voice`. An explicit new-project request creates a new workspace. Named-project ambiguity calls for one question. Foreground-window guesses are not a substitute for an authorized directory. Retried submissions must not create duplicate tasks or folders; failed/cancelled workspaces remain available.

One active job is a product constraint. A second explicit work request must ask the person to finish or stop current work; it must not silently replace or queue it. A late correction must not silently become a new turn. After daemon loss, work remains interrupted until explicit Continue. This is saved-thread recovery, not an independent durable worker service.

## What actually worked

The installed candidate is Voice `0.1.5-12`, built from runtime `c7de65fb` and recipe `17bf680`, with Codex `0.153.4-1`. Later documentation or merge commits do not change these tested bytes. The full pinned source suite ran 322 tests: 320 passed and two expected platform checks were skipped. UI/controller/orb and package checks also passed. Exact logs, screenshots and archive identities are in the evidence handoff, not committed as raw private data.

| Outcome | Evidence and limit |
| --- | --- |
| Form-free intake | Actual installed Type UI submitted a tracker request without a folder/project form and created its workspace automatically. Talk/Type rendering was inspected. This does not prove microphone transcription. |
| Real execution | Existing account/model ran Codex and produced the task tracker HTML. The actual task, child, thread and turn were observed. Initial configured-model incompatibility required a supported CLI upgrade, not a silent model switch. |
| Shared control foundation | A typed request to add All/Active/Completed filters was accepted on the same running turn. Spoken correction remains unverified. |
| Concurrent conversation | Gemini answered an unrelated typed question while the same job continued, without creating a second job. Physical audio concurrency remains unverified. |
| Human approvals | An exact file-change request was approved through the installed UI keyboard path. A denied long command recovered into a reviewable test script and short invocation. |
| Recovery | Actual installed daemon restart interrupted a follow-up and cleared stale approval. Explicit Continue resumed the same saved thread. Cancellation cleared pending approval and preserved the artifact; stale approval responses were rejected. These recovery checks used the control API. |
| Usable live task view | Real Quickshell fixtures exposed and then verified fixes for draft loss, caret/selection reset and approval-button focus loss during updates. Fixture state is not a real agent or physical-audio pass. |
| Inspectable result | Artifact existence is tracked separately from behavior. Reviewed non-browser tests passed for task actions, filters and simulated persistence/storage failures. Browser layout and actual reload persistence are unverified. |
| Configuration preservation | A Codex trust side effect was reproduced, removed from the test configuration and fixed. Real isolated app-server tests verify exact cwd, policies, existing project configuration and unchanged trust bytes without inference. |
| Local delivery | Package contents and installed source were compared; readiness and the final installed UI were inspected. Prior packages remain available. No public package channel or ISO was published. |

The initial source calculator run and the final installed tracker run are different evidence. Earlier candidate screenshots, real sessions, final source tests and installed package checks must not be combined into an imaginary single fully accepted run.

## What failed, what we learned and what to avoid

| Failure or discrepancy | Lesson and future rule |
| --- | --- |
| Automatic folders existed in the backend, but the first focused UI control was still a folder field | Test the whole journey from initial entry through delegation. Making a form optional does not make the experience conversational. |
| A visual pass checked only the running-task view | Include first-use Talk/Type, delegation transition, live intervention, approval, result and recovery. A screenshot of one good panel is insufficient. |
| Installed code differed from the source being discussed | Inspect installed versions and hashes first. Keep source, preview, daemon, package and installed revision identities explicit. |
| Codex launched and created a thread, but could not run the configured model | Process readiness, authentication and model compatibility are separate. Check the real execution path; preserve configured model and billing choices. |
| Gemini typed replies left the UI looking like it was speaking | Provider state labels are not proof of actual audio playback. Test typed-only sessions separately from microphone/speaker sessions. |
| Streaming text was fragmented and repeated | Coalesce deltas using exact message/thread/turn identity; prefer the final-answer phase for the report. Keep bounded private history separate from redacted audit logs. |
| Task refreshes destroyed unsent text, caret selection or keyboard focus | Exercise real typing while events arrive. Preserve task-keyed drafts and selection; restore focus only when appropriate and cancel stale deferred focus work. |
| A focus generation changed after the request signal | Event order matters in QML. Add a regression for ordering and validate it in the actual renderer, not only source-pattern tests. |
| File approvals arrived before their matching lifecycle detail | Match thread/turn/item identities and allow only a bounded wait for detail. Decline unusable requests rather than presenting vague approval text. |
| A long command was silently truncated at 4,000 characters | Never ask someone to authorize an undisclosed command tail. Decline oversized command detail; use shorter commands or a reviewable script. Mark file-preview truncation explicitly. |
| Delayed conversation controls followed a later UI task selection | Bind controls to the daemon-selected task at final-transcript capture. Only a submission receipt can associate a new same-turn task. Recheck provider generation after waiting for the action lock. |
| Queued direct work could restart and approvals could survive daemon loss | Reconcile all active direct states on startup. Preserve history and thread identity, clear stale approvals and require explicit Continue. |
| Codex automatically persisted Trusted for a writable explicit thread cwd | Test configuration side effects, not only requested policies. Omit redundant thread/start cwd because the dedicated process already owns the exact directory; preserve existing trust and verify against the installed protocol. |
| The first post-install readiness request failed | Keep the failure record. A clean post-install restart resolved it, but the proposed package-replacement race is not a confirmed root cause. Do not upgrade hypotheses into facts. |
| Local browser access was denied by tooling policy | Respect the restriction; do not route around it with another browser/server. Report non-browser checks accurately and retain a manual browser acceptance gate. |
| Preliminary test helpers omitted production lifecycle or crashed on changing approval state | Verify the helper's lifecycle and negative controls before a paid run. Separate helper defects from product failures and keep failed evidence. |
| Earlier records called multiple different candidates “current” | Maintain one current index and date historical checkpoints. Source merge, local installation and public release are different milestones. |

Do not weaken checks, widen agent permissions, trust arbitrary directories, bypass OS authentication, change provider billing, copy code into installed paths, or add dependencies just to make a demo appear successful. Keep build outputs, credentials, raw private histories and recordings outside Git. A user-approved source merge does not authorize package publication or an ISO rebuild.

## Remaining acceptance and iteration order

1. Physical Lenovo journey: real microphone/speaker, one spoken new-app request, unrelated conversation during work, one spoken and one typed correction, understandable pause-time updates and a short reviewed recording. Check original transcript, task identity and resulting requirement; do not substitute typed/synthetic input.
2. Browser result: open the produced HTML through a permitted user workflow and exercise add/complete/delete/filter/reload behavior. Check appearance and keyboard operation. File existence and DOM stubs are not this gate.
3. Real missing-auth/setup recovery and spoken launch/refocus; native Stop/Continue interaction; remaining Orb state, interruption and reduced-motion/accessibility acceptance. A binary being installed is not account readiness.
4. Revisit the one-time autonomy preference explicitly. Existing agent prompts remain enabled. Forms, meaningful clarification and permission decisions are different kinds of friction.
5. Only after the basic loop is reliable, consider broader providers, independent workers, parallel jobs, user-controlled memory and proactive research with budgets. Reuse the task and capability boundaries rather than building another competing harness.

Universal memory, meetings, dictation, Composio expansion, automatic agent installation/authentication, arbitrary development-server management, native app takeover and proactive parallel agents remain deferred. A single onboarding experience is a product aim; universal access from a single vendor subscription has not been established.

## Definition of success for the next iteration

A person can state a reasonable outcome, understand whether Maslow is listening or working, make one correction, inspect useful output and stop or recover work without managing project bookkeeping. Measure successful completion, unnecessary questions, correct correction delivery, perceived responsiveness and honest result verification on a frozen scenario. No latency target, accessibility claim, uniqueness claim or complete hardware acceptance is established by this MVP yet.

The [September 20 integration closeout](handoffs/2026-09-20-voice-merge.md) records the later task-binding correction, source/package integration and CI limitations separately from the installed 0.1.5-12 evidence above.
