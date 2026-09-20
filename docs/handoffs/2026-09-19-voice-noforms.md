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
