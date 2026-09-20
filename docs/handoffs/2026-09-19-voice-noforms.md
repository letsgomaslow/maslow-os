# Voice: remove routine intake and verify the actual delegation path

This follow-up addresses the reported gap between automatic workspace support and a UI that still looked like a task form. It remains local development, not an installed or publicly released acceptance result. The installed Lenovo packages are Voice `0.1.5-7` and Codex `0.152.0-2`.

## Changes and scope

Gemini's ordinary Talk and Type paths no longer present folder/context intake. Request overrides remain available in Settings. The conversation prepares the brief and chooses routine defaults, including a self-contained browser app for an unspecified simple application. Brainstorming does not authorize work; material ambiguity still permits a conversational question.

The selected task puts intervention controls ahead of bounded activity and the expandable agent report. Technical IDs and workspace paths remain inspectable. Assistant deltas from the same Codex message coalesce into readable activity entries. Typed Gemini replies return the UI to ready without falsely claiming that audio is playing.

Existing agent permission policies, provider/model/billing settings and credentials remain unchanged. Automatic workspace preparation does not constitute consent to loosen execution permissions. A one-time autonomy preference was requested; no answer has been recorded at this checkpoint.

## Real production-path evidence

Private evidence root: `/tmp/maslow-voice-noforms`. Helpers use isolated state and runtime sockets, existing Secret Service credentials, the production provider factory and `VoiceService.run()`. No installed service or shell was replaced.

The source native UI received `Use Codex to build a simple calculator app.` through actual keyboard input. It created task `796ba79f-50de-4319-8820-8e05f5ab45c5`, workspace `ui-run-3/projects/simple-calculator-6104ed28f6`, Codex thread `01a0bc59-3c7f-7051-a6e4-1bf63d4f10d2`, and turn `01a0bc59-3d05-7762-932f-635e57cac6b4`. No folder, project name or task form was filled in. The actual task view opened and showed live activity and approvals.

The task completed with `index.html`, `calculator.js` and `style.css`. Exact routine command/file approvals were reviewed individually; this was not unattended execution. Codex's command output reported nine passing logic checks. The coordinator independently ran nine Node assertions covering addition, subtraction, multiplication, division, decimals, division by zero, pocket-calculator chaining, backspace and clear; all passed. These checks exercise the calculator module, not browser DOM/input behavior. Maslow's artifact records verified file existence, not behavior. A subsequent correction was correctly rejected with `STEERING_UNAVAILABLE` because the turn had already completed; it did not silently create another job.

Browser automation rejected the local file URL under its security policy. No alternate browser surface or server workaround was used by the coordinator. A pending Codex localhost-server command was explicitly denied. Browser behavior and appearance remain unverified; the agent's final report records that limitation. This does not pass the plan's browser-artifact acceptance gate.

The production daemon for this run loaded the earlier in-progress source before the subsequent activity-coalescing and typed-state fixes. Its task result must not be represented as final-candidate acceptance. The real UI was refreshed independently while the daemon retained the same task identity.

## Compatibility and diagnostics

For this isolated run, the official Omarchy Codex `0.153.4-1` archive was downloaded, its detached signature verified against the trusted Omarchy key, and its extracted binary selected only in the test process PATH. It successfully used the existing configured model and sign-in. The host package was not upgraded. Archive and extraction: `/home/maslow/Maslow-ai-os/voice-mvp-build/codex-0.153.4`.

Two preliminary calculator helpers did not establish acceptance: the first omitted the production service lifecycle and therefore its agent router; the second crashed on a transient cleared approval while inspecting a denied request. Failed runs and logs are retained separately. Neither is attributed to a product execution failure.

A separate real Gemini typed-only diagnostic reproduced the SDK remaining in `speaking` after a finished text reply. The corrected diagnostic returned UI state `listening`, microphone false, speaking false, and zero tasks for `What is two plus two? Answer in one short sentence.` The answer was correct. This proves typed-state recovery and conversation/task separation, not physical audio.

Frozen corrected probe: `/tmp/maslow-voice-noforms/typed-state-probe-2.py`, SHA-256 `d8681a6bfa43deeb5debe5b307f39d2bad51b7b3324e90edbfdde6afef4791da`. Result: `typed-state-run-2.log`. Native UI daemon helper: `ui-daemon.py`, SHA-256 `54a4422e002aa8267589bafad6be26fc304cbbdcba8ffeab5f2eee6d081578e4`. The isolated daemon and its source UI were stopped cleanly after completion; the installed service and shell were untouched.

Artifact hashes: HTML `d6f1203ecdb802fdc4580f4be81ad03974ca8a04fcf0214dfd7f66acd091f167`; calculator JS `5851726ae5479f3bb640ddf6d599d6cd312df588343474dc355d7c8d4cff756b`; CSS `2c769ebe32c7d964078ca98178d73ee45ca4b7f03e472f3c7f7f5e84272c7a04`. Extracted Codex archive SHA-256: `8e00aa8c1e42bd6d06896bf684b337734d11f8703e986fd0fbca8502fd36ad57`.

Inspected native screenshot `/home/maslow/Pictures/screenshot-2026-09-19_21-17-30.png` shows the actual completed task, Continue/Open folder controls and each artifact explicitly marked `File exists; behavior not verified`. Its stale Speaking header came from the already-running pre-fix provider; the separate corrected live probe above verifies the fix.

## Final source, visual checks and package

Source commits: `075c8cd7` (conversational intake and typed Gemini readiness), `d0be3112` (readable Codex streams, final reports and exact file-change approvals), and `83bcd1382a6c4b8e99e5dce84be6d4d02d922728` (form-free Gemini UI, bounded approval/report/activity, provider regression repair and one-shot keyboard focus). Two Terra workers handled disjoint UI and approval-detail changes; the coordinator reviewed, integrated and visually tested them.

The final pinned suite ran 319 tests successfully with two expected platform skips; controller/UI/orb checks and `git diff --check` passed. Log: `/tmp/maslow-voice-noforms/final-tests.log`. The final one-line focus-outline color change was checked through the UI contract suite and the running Quickshell render after that full run. Existing physical-audio/provider gates are not replaced by this result.

Final fixture used real Quickshell/software rendering on Lenovo, copied from the source UI into `/tmp/maslow-voice-noforms/final-preview`. Inspected screenshots under `/home/maslow/Pictures/`:

- `screenshot-2026-09-19_21-21-00.png`: Gemini Type has only the focused message input and Send; no routine folder/context form.
- `screenshot-2026-09-19_21-21-05.png`: 4,000-character approval text stays inside a bounded scroll area, with task input and controls visible. The selected task input received focus.
- `screenshot-2026-09-19_21-21-28.png`: explicit non-Gemini folder repair focuses its visible field; ordinary non-Gemini conversation is no longer disabled by an empty folder.
- `screenshot-2026-09-19_21-21-50.png`: Talk offers Start talking without project intake.
- `screenshot-2026-09-19_21-22-26.png`: final source shows a contrasting keyboard focus ring on Approve. Tab from task input followed by Return emitted only the displayed task's `fixture-approval` request. Replacing task data did not refocus the input after focus had moved away.

These are fixture rendering/keyboard checks, not physical speech or real-agent approval acceptance. The initial temporary preview layout failed because its import escaped Quickshell's config folder; the temporary wrapper was corrected, with no source workaround. The final preview loaded without QML errors, emitted only an unrelated portal registration warning, and was stopped after verification. No shell configuration was changed.

Codex file approvals now wait briefly for their exact thread/turn/item lifecycle event before displaying path/kind/diff previews. Missing usable details cause a declined request instead of a generic approval. Previews explicitly identify truncation. Protocol regressions exercise interleaved identities and the notification/callback race. Permission policies are unchanged. Final reports prefer the schema's `final_answer` phase; fallback messages retain paragraph boundaries.

Local candidate:

- Runtime input: `83bcd1382a6c4b8e99e5dce84be6d4d02d922728`.
- Recipe input: `370947f` in the package repository, only Voice pkgrel `8 → 9`.
- Archive: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-noforms/maslow-voice-0.1.5-9-x86_64.pkg.tar.zst`.
- SHA-256: `b2a5f8e5b83fc0b94dac0259c3ab48da2ee018f787bbafd1bd67cdd37a1640cb`.
- Normal makepkg build/check/package completed in `maslow-voice-mvp-builder`, retaining dependency checks and pinned Python hashes. No dependencies were added. Build log: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-noforms-build.log`.
- Extracted archive matched all 41 runtime/UI source files; version-specific plugin entry points and compiled shader were verified. Package invariants passed; log: `voice-mvp-build/noforms-package-checks.log`.
- Voice `0.1.5-7` rollback and earlier `0.1.5-8` candidate remain intact at the paths and hashes recorded in [the MVP handoff](2026-09-19-voice-mvp.md).

## Remaining acceptance

Outstanding gates: compatible installed Codex, separately scoped local package rollout, real microphone/speaker interaction and recording, concurrent conversation and spoken correction, browser artifact behavior, missing-auth recovery, cancellation, and restart followed by explicit saved-thread Continue. The user must not be asked to fill routine project forms to complete any normal Gemini request.

No publication, ISO rebuild, broad agent-policy change or automatic recovery is included. The candidate is not installed. A concrete local rollout question was presented after archive verification, following the original plan's separate-rollout boundary. Installing the signed Codex update also needs that decision: its prior `0.152.0-2` package is absent from cache and the official repository returned 404 for the old archive. Preserve prior Voice packages and the user's unrelated discussion documents. Next action: receive the local rollout decision, then install through the supported privileged package flow and verify installed bytes before physical acceptance. The separate one-time execution-autonomy decision remains unanswered.

## Recovery correction: current candidate is 0.1.5-10

Further recovery review found that queued direct-agent work could restart automatically and interrupted tasks could retain stale approval prompts. Runtime `aeb7dbe6e2b9756b50211d04ffb4462f30daa336` corrects both: persisted queued/running/approval-waiting direct tasks become interrupted, live approval fields are cleared, and active child records become interrupted. Thread/turn identities, workspace, earlier completed children, activity and historical approval events remain intact. Unstarted proposals retain their explicit Start action. No automatic continuation is added.

Regression coverage reopens the SQLite store and checks ten agent/state combinations without invoking the client factory. Focused routing/task tests passed 35 tests. The final pinned suite ran 320 tests successfully with two expected skips; controller/UI/orb checks and whitespace validation passed. Logs: `/tmp/maslow-voice-noforms/recovery-tests.log` and `recovery-final-tests.log`.

An isolated production daemon process also loaded two synthetic persisted jobs through its actual startup lifecycle and Unix watch socket. Both returned interrupted with saved history and identities, no stale approval, and no automatic agent work. Its PATH excluded agent binaries; no account or inference was used. Frozen helper: `/tmp/maslow-voice-noforms/recovery-startup.py`, SHA-256 `57b8894bcdc9c3ae9a6d312a6dce6ac513e2bf7104c2822a770d58a0b196a68e`. Result: `/tmp/maslow-voice-noforms/recovery-startup/result.json`. This is startup recovery integration evidence with synthetic tasks, not a real Codex crash/Continue pass.

Rendering that recovered data was attempted in a separate Quickshell preview, but the Lenovo session had become securely locked and screen capture waited. The owned preview and capture processes were stopped; the lock was not bypassed. No recovery screenshot was accepted. The earlier UI screenshots still apply to unchanged UI bytes, but a directly observed recovery-screen check remains pending.

Replacement local candidate (supersedes uninstalled `0.1.5-9`):

- Recipe: `68ac182152502fd33d9cc509498b14f28724e9df`, only Voice pkgrel `9 → 10`.
- Archive: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-recovery/maslow-voice-0.1.5-10-x86_64.pkg.tar.zst`.
- SHA-256: `1addfaf0eac6c2af9e97c66052a10ea583d517ae990eb04f4234aa3d18413170`.
- Normal makepkg build/check/package and package invariants passed. Logs: `voice-mvp-build/voice-recovery-build.log` and `recovery-package-checks.log`.
- All 41 extracted runtime/UI files match source; versioned entry points and compiled shader were verified. Earlier candidates and rollback package are preserved.

The current candidate remains uninstalled. The pending rollout question now has this corrective candidate as its target; no response or execution-autonomy choice has arrived. No permission policy, credential, installed package, public channel or ISO changed. Next action: obtain the local rollout decision and an unlocked desktop, then install through the supported package flow and finish native acceptance. The overall goal remains active and unproven.

## Authorized Lenovo rollout and installed task check

The user’s subsequent “continue” authorized the pending local rollout. Installed through the desktop privilege flow: `maslow-voice 0.1.5-10` from the recovery archive above and signed `openai-codex-bin 0.153.4-1` from the verified official archive above. All 41 installed runtime/UI files matched the tested source. Hash-only before/after checks confirmed Voice settings and Codex configuration were unchanged. Quickshell PID 1477 remained running; the supported launcher rescanned the plugin. Local installation evidence is under `/home/maslow/Maslow-ai-os/voice-mvp-build/rollout-0.1.5-10/`, including `install.log` and private hash-only `settings-before.json`. No public package, ISO, credentials, or permission policy changed.

The first installed readiness request returned `CONTROL_FAILED`. Isolated readiness checks passed, including with the running service environment, and a clean user-service restart after installation cleared the failure. A daemon started while package files were being replaced is a hypothesis, not a confirmed cause. Preserve this initial failure separately from subsequent successful readiness and execution.

The actual installed Type page submitted a single-file task tracker request without project, folder, or details forms. Gemini created `/home/maslow/Projects/Maslow Voice/build-a-simple-local-task-tracker-as-a-single-in-93545c926e` automatically. Task `b29cccac-778c-4f6b-bda8-9c765ca96847`, child `9d18bc1f-41a8-4f73-8445-3f2d9ffb0c10`, Codex thread `01a0bc7f-3626-7b90-a2d0-95a637be2bfb`, and turn `01a0bc7f-36b7-7c43-9d6d-7850278b302f` were observed in authoritative state. Typing “Also include All, Active, and Completed filters.” into the displayed task input produced an accepted instruction on the same task/thread/turn. Gemini then answered an unrelated typed arithmetic question correctly while that one job continued; no extra job was created.

Individual agent approvals remain enabled. Read-only workspace inspection requests were inspected and approved by exact request/child identity. The exact `index.html` file-add preview was inspected in the installed UI and approved with Tab/Return from the task input; subsequent state confirmed the file change completed and the artifact exists. This is actual installed keyboard approval evidence, separate from fixtures. Browser tooling had rejected local-artifact access in the earlier run; no alternate browser or server workaround is authorized by that refusal. The agent was instructed to perform non-browser checks and report browser behavior as unverified.

Inspected installed screenshots in `/home/maslow/Pictures/`: `screenshot-2026-09-19_21-44-52.png` preserves the initial readiness failure; `21-47-20` shows ready form-free Type; `21-47-50` shows the real selected task and exact command approval; `21-48-34` shows the typed correction; `21-50-25` shows the file-change preview with visible controls and task-input focus (all share the full filename prefix/date and `.png` suffix). These screenshots establish rendered UI and keyboard interaction, not physical speech.

A physical voice check was requested from the user while the task ran; no result has been received. Spoken correction, microphone/speaker quality and recording remain open. The one-time autonomy choice remains unanswered; existing Codex permissions have been preserved.

The installed tracker completed. Artifact SHA-256: `38b111a106d0787dd063880fe0d43b26e70eff745b2e0201d5f67815be8f981d`. The agent reported non-browser checks passed, and the coordinator inspected and independently reran the same script successfully: syntax, no external script/style dependencies, empty-input handling, literal HTML input, add/complete/uncomplete/delete, filters/counts, simulated reload persistence, malformed stored data, and read/write storage failures. DOM/storage were simulated, so this is repeat execution of agent-authored checks, not an independent browser test. Retained script SHA-256 `660ee444386efdc340f1bc016d114d53ff5c86c4511951a576a57fe395512969`; script/log are in `voice-mvp-build/installed-tracker-evidence/`.

A live long inline test command exposed silent 4,000-character approval truncation. The coordinator denied request `6b062513-1e04-4701-8786-e1f789c8e709` rather than approving hidden command text. Codex accepted the correction, wrote a separately reviewable temporary test script, and ran it only after its full content and short invocation were inspected. This establishes denied-approval recovery on the installed agent. Source correction `6de2cd2d` declines oversized command approvals before presenting them; exact-limit/oversized/direct/observed/reason-fallback regressions passed within 29 execution tests. Existing explicitly truncated file-change previews and agent policies remain unchanged.

Installed recovery/cancellation checks used explicit read-only follow-ups to the completed tracker, with Voice disabled. Attempt 1 resumed the original thread and paused at an exact title-inspection approval. Restarting the production user service changed the task and active child to interrupted, cleared approval, retained prior completed child/report, workspace, and all thread identities, and did not start work automatically. An old approval response was rejected with `TASK_NOT_RUNNING`. Explicit Continue created attempt 2 on the same original thread, turn `01a0bc86-0353-7751-82fd-c09b0d2d3296`, child `7e5ac9c4-62be-4e62-8323-720e010c8dc5`. Cancel changed both parent and child to cancelled, removed its pending approval, and retained the artifact. Responding to that stale approval was also rejected. These are actual installed control-API/agent checks; native Stop/Continue keyboard interaction and physical voice are separate gates. A final explicit Continue was requested to leave the task with a useful completed summary.

Final installed acceptance follow-up completed as attempt 3, child `f770ebc1-9bfd-461b-b6f7-a8679a2d63e9`, turn `01a0bc86-6bf1-7f83-a675-839979a3a233`, still on the original thread. Its short read-only title command was reviewed and approved by exact request identity. The final result correctly identifies `Local task tracker`, links the existing HTML and retains the browser-verification caveat. Sanitized final task/attempt identities are retained in `voice-mvp-build/installed-tracker-evidence/final.json`.

## Live-activity typing and approval reviewability correction

Source `bb175544` preserves unsent task drafts, cursor/selection and active task controls across streamed task-model replacement. Initial visual iterations exposed cursor reset, lost action-button focus, and a generation increment occurring after its focus-request signal; each was corrected before freezing the source. The final real Quickshell fixture retained middle insertion (`ABCDE`, cursor 3, refresh, type X → `ABCXDE`), retained a selected range for replacement (`ABCZDE`), and retained the visible Approve focus ring while leaving input focus clear. The final two inspected screenshots are `/home/maslow/Pictures/voice-draft-focus-final.png` and `voice-draft-focus-final-approval.png`. Their left panel is synthetic source-fixture state; their right panel is the separate installed completed task. The fixture was stopped afterward; no installed UI/source was edited for the experiment.

One Terra worker owned UI/fixture changes; one Astra worker owned the bounded command-approval correction. The coordinator reviewed their diffs and visual evidence, ran combined checks, and owns integration. The combined pinned suite ran 321 tests successfully with two expected skips; UI/controller/orb checks passed. After the final two-line QML signal-order correction and its regression, focused UI/controller/orb checks and whitespace validation passed again; unchanged Python tests were not repeated. Log: `voice-mvp-build/reviewability-tests.log`. The command approval correction is `6de2cd2d`; no provider, credential or agent permission policy changed.

## Installed corrective package: 0.1.5-11

- Runtime input: `bb175544` (including `6de2cd2d`); recipe input: `d40d822`, Voice pkgrel 11 only.
- Archive: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-reviewability/maslow-voice-0.1.5-11-x86_64.pkg.tar.zst`.
- SHA-256: `5ab000edd9646eaf0de411adc0e352afbf8a293b49bacf8b29dd9ba5a33cbc93`.
- Normal makepkg dependency/build/check/package steps passed; package invariants and recipe syntax passed. Logs: `voice-reviewability-build.log`, `reviewability-package-checks.log` under `voice-mvp-build`.
- All 43 checked runtime/UI/Hermes-plugin files match source in both archive and installed filesystem; versioned plugin entry points and compiled shader verified. The earlier count of 41 excluded the two Hermes-plugin files.
- Installed through the desktop privilege flow after the task completed and Voice was disabled. A clean post-install daemon restart reported ready, with the completed task/history intact. The supported launcher rescanned the installed plugin. Screenshot `/home/maslow/Pictures/screenshot-2026-09-19_22-03-29.png` was inspected: real completed job, visible Continue/Open folder/report/artifact controls, and truthful “File exists; behavior not verified” label. Local install log: `voice-mvp-build/rollout-0.1.5-11/install.log`.
- Prior packages, including 0.1.5-10 and rollback 0.1.5-7, remain intact. The package builder and all owned source previews are stopped. No public publication or ISO rebuild occurred.

Final configuration checking found one additional Codex project-trust section for the automatic test workspace, timestamped exactly at the initial thread start. Removing only that section reconstructed the pre-test configuration hash exactly. The coordinator removed that test-added trust entry and verified the complete original Codex configuration and unchanged Voice settings against their earlier hashes. Voice itself has no project-trust writer and supplied explicit `untrusted` approvals on every turn; individual approvals were observed throughout. Do not describe the entire execution as having left the configuration untouched: it was restored at closeout. The cause/recurrence of Codex’s trust persistence requires compatibility review before a broad policy-preservation claim.

Remaining acceptance: physical microphone/speaker conversation and recording, spoken correction, voice-driven launch/refocus, actual browser rendering/reload behavior, and real missing-auth recovery. Installed execution, typed concurrent conversation/steering, exact keyboard file approval, denied approval recovery, cancellation, and real restart plus explicit saved-thread continuation have evidence above. Controls after the UI correction were visually verified with fixture state; do not conflate those fixtures with spoken interaction. Next action: physical Voice acceptance using the installed candidate, after resolving the documented trust-persistence behavior as needed. The one-time autonomy preference is still unanswered and has not been applied.

## Codex trust-persistence compatibility correction

The cause is confirmed in [Codex 0.153.4 thread/start](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server/src/request_processors/thread_processor.rs#L1321): an explicit request cwd, no existing project trust, and write access to that cwd trigger persistent Trusted configuration, regardless of approval policy. This is upstream behavior, not a Voice config writer. The dedicated Voice app-server already launches in the exact task workspace. Omitting only the redundant new-thread cwd prevents that automatic trust change while preserving effective cwd and existing trusted/untrusted configuration. Resume requests remain unchanged.

A real installed Codex probe used empty temporary homes and no credentials or inference. The explicit-cwd positive control reproduced trust persistence; omitted-cwd unconfigured, trusted and untrusted cases retained their exact configuration. Probe: `/tmp/voice-codex-trust-probe.py`, SHA-256 `61b20a39b52462d88c3ee78d05f613831eaa0516df20cdeeb728f4a3d4f2b1fb`. A committed regression exercises the actual adapter with the installed app-server, stops locally before turn/start, and checks unchanged config bytes, exact cwd, untrusted/user/workspaceWrite/network-disabled policy, and preserved trusted-only project configuration loading. This requires an installed Codex executable and explicitly skips when it is absent; the always-run mock contract independently binds cwd to the process and checks omission from thread/start. Focused execution tests passed 30 tests with zero skips on this Lenovo.

Final source `c7de65fb` passed the complete pinned suite: 322 tests ran successfully with two expected skips, plus UI/controller/orb and whitespace checks. Log: `voice-mvp-build/trust-final-tests.log`. The trust regression ran against real installed Codex, not a skip. Unchanged UI bytes retain the earlier native/fixture evidence; installed 0.1.5-11 Type was additionally inspected in `/home/maslow/Pictures/screenshot-2026-09-19_22-05-53.png` with only a focused message field and Send message, no folder form.

Corrective candidate `maslow-voice 0.1.5-12` uses runtime `c7de65fb` and recipe `17bf680`. Archive: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-trust/maslow-voice-0.1.5-12-x86_64.pkg.tar.zst`; SHA-256 `4db9c8a18e63d741167cf1aee19c277b2fc39ff1a202ea03101d32aa395eb99a`. Normal dependency/build/check/package steps and package invariants passed. Extracted archive matches all 43 checked source files; versioned entry points and compiled shader verified. Logs: `voice-trust-build.log` and `trust-package-checks.log`. Builder stopped afterward; earlier archives preserved.

Local rollout of 0.1.5-12 is waiting at the operating system's desktop password prompt, inspected in `/home/maslow/Pictures/screenshot-2026-09-19_22-10-01.png`. This is OS authentication for already-authorized work, not a request to change agent permission policies. No password was requested in chat or bypass attempted. Until package-manager success and installed-byte/readiness checks, 0.1.5-11 remains the installed version and 0.1.5-12 is a tested candidate. Next action: complete desktop authentication, verify installed 0.1.5-12 bytes/settings/readiness and rescan through the supported launcher; then perform physical speech and browser acceptance. The overall feature remains unproven until those gates close.

Desktop authentication subsequently completed successfully. Voice `0.1.5-12` is now installed; all 43 checked installed files match source, versioned entry points and shader verify, and Voice settings plus the original Codex config match the pre-test hashes. The restarted service reports ready with Voice disabled, no error, and the completed tracker/attempt history preserved. The supported launcher rescanned the installed plugin. `/home/maslow/Pictures/screenshot-2026-09-19_22-11-25.png` was inspected after installation and shows the real completed task and available result controls. Install log: `voice-mvp-build/rollout-0.1.5-12/install.log`. This closes the preceding OS-authentication/installation gate; no further installation approval is pending. Next action is physical speech and browser acceptance. The overall feature is not yet fully accepted; existing agent permission prompts remain unchanged.
