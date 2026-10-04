# Gemini voice and conversation preferences — September 22

## Scope and implementation

User requested simple voice and prompt settings. Source branch: `codex/voice-preferences`, based on runtime merge `223d0daa2487da5e884cb339f35d306af3564e96`. This paragraph records the initial source-only checkpoint; the authorized preview and rollout follow below. No dependencies, provider switches, credentials, model selection, permission policies, package recipes or installed files changed.

Gemini already accepted the saved `gemini_live_voice` preference. Settings now offers Google's 30 documented voices, retaining Puck by default. Unknown previously saved voice names remain displayed instead of silently selecting a replacement. [Google Live capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) says native audio supports the [TTS voice catalog](https://ai.google.dev/gemini-api/docs/speech-generation#voice-options); documentation checked September 22.

The new `gemini_live_prompt` preference changes the initial conversation instructions. Existing settings inherit the previous default. Empty prompts fall back to that default. Existing string validation rejects non-string values, NULs and more than 4,096 characters. The app/task operational instructions are appended independently; prompt customization does not remove tool boundary checks.

The UI has a voice dropdown, multiline conversation prompt, Save prompt and Reset default. Voice saves on selection. Prompt saves explicitly; reset saves the original prompt. Controls are disabled during conversation or active work, matching the daemon's existing configuration restrictions. Settings take effect in the next conversation. This is optional personalization, not a form required before delegating work.

## Verification

- Pinned Voice suite: 330 tests passed with two expected skips; UI and orb contracts passed.
- After adding an additional named-voice SDK construction assertion: focused configuration/Gemini suite passed all 39 tests. Zephyr reaches the actual pinned SDK's voice option; this does not prove remote synthesis.
- Controller test and `git diff --check` passed.
- A separate native Quickshell fixture rendered the actual changed Panel on unlocked Lenovo Wayland. Keyboard selection sent `gemini_live_voice: Zephyr`; typing and Save sent the exact custom prompt; Reset sent the original default. Requests were captured by the fixture, not sent to the installed daemon.
- Inspected screenshots: `/home/maslow/Pictures/screenshot-2026-09-22_10-41-50.png` (default), `/home/maslow/Pictures/screenshot-2026-09-22_10-42-06.png` (edited prompt/selected voice), and `/home/maslow/Pictures/screenshot-2026-09-22_10-42-42.png` (conversation guard). Labels, wrapping, input and buttons fit the panel.
- Preview initially failed because its imported UI was outside the config directory; putting the fixture at the copied config root fixed it. Preview used the orb's fallback because the copied source lacks the compiled shader; no orb changes are part of this work.
- No live Gemini call, physical listening comparison, package build, installation or publication was performed. Installed Voice remains the previous package; the settings are source-only.

## User journey and next step

Once rolled out: open Voice → Settings, choose a voice, edit the conversation prompt if desired, press Save prompt, and start a new conversation. Example: “Speak calmly. Keep answers brief and ask one question at a time.” Reset default restores the original style.

Next action: build and install a local candidate through the normal separate rollout, then compare Puck and Zephyr in physical conversation and confirm the saved style survives a daemon restart. Keep automated/fixture evidence distinct from audible provider acceptance. Do not promise exact accent, emotional delivery or consistent obedience to every stylistic request based only on settings tests.


## In-settings preview and authorized local rollout

The user requested installation and a voice preview without leaving Settings. Runtime `ef5a30936efadeb16beecffe09893792622fb0d6` includes the preferences plus preview; recipe `3a8db0a4cfda06364d6120b337be2de2195daf49` produces `maslow-voice 0.1.5-14`. Source commits remain on local `codex/voice-preferences` branches, with no push or merge.

The selection workflow now supersedes the earlier save-on-selection UI: select a voice → Play preview → Use this voice. Choosing a voice alone does not save it. Stop preview cancels playback; the fixed sample has no tools, no microphone capture, no task creation and no preference writes. It uses the pinned Google SDK with the existing Gemini Live model and Google account, not a separate TTS model or billing route. Account lookup and playback have bounded timeouts. Errors are sanitized. Active conversation/work and configuration changes exclude preview; the speech-stop and end-voice controls also stop it. Cancellation stays bound to the playback task even if a later preview starts.

Final pinned suite: 337 tests passed with two expected skips. Controller/UI/orb checks, package invariants and whitespace checks passed. Preview tests cover output-only transport, real SDK request types, selected voice, no tools, missing account, invalid voice, active work, completion/error, stop and replacement-task cancellation. The existing audio test confirms `capture=False` opens only a speaker stream.

Native Quickshell fixture screenshots `/home/maslow/Pictures/screenshot-2026-09-22_10-54-31.png` and `10-55-25.png` (same prefix/date) show preview selection and Playing/Stop states. Keyboard activation emitted the selected Zephyr preview request and Stop request. No preference write accompanied preview. Fixture playback does not establish remote synthesis or physical audio. One worker exhausted its usage allowance before making preview changes; the coordinator implemented and verified that work directly.

Final local archive: `/home/maslow/Maslow-ai-os/voice-mvp-build/voice-preferences/maslow-voice-0.1.5-14-x86_64.pkg.tar.zst`; SHA-256 `36107d46b085168ac868e480484b7e54c5865695808cd41e507524dcefb7ac4a`. All 44 runtime/UI files match source; versioned entry points and compiled shader verified. Normal makepkg dependency/build/check/package stages passed. Logs: `voice-preferences-build-final.log` under that evidence root and `/tmp/voice-preview-tests-final.log`. The prior `0.1.5-12` archive is retained at `voice-mvp-build/voice-trust/` for rollback. Builder and owned preview stopped before audio testing.

Installation is authorized but currently waiting for desktop authentication: the shell reports a secure locked session. The daemon was idle with no active work before the rollout and was stopped before invoking the package manager. No lock bypass was attempted. Hash-only configuration evidence and installation log are under `voice-mvp-build/rollout-0.1.5-14/`. Until package-manager success and installed-byte verification, `0.1.5-12` remains the installed version. Next action: unlock/authenticate, verify installed bytes and unchanged settings, restart the service, refresh through the supported launcher, and exercise the real preview.


## Installed and exercised on Lenovo

Desktop authentication completed. Package manager installed `maslow-voice 0.1.5-14` successfully. All 44 installed runtime/UI files match source `ef5a3093`; versioned manifest and compiled shader match the archive. Hash-only checks confirmed Voice settings and Codex configuration were unchanged. The service restarted cleanly and reported ready. The supported launcher refreshed the plugin and opened Settings; inspected installed screenshot: `/home/maslow/Pictures/screenshot-2026-09-22_10-58-56.png`.

Actual installed Settings keyboard checks used the real saved Google account and current Gemini model. Puck transitioned connecting → playing → idle. Selecting Zephyr and pressing Play reached playing; pressing Stop returned idle. Neither preview changed the saved voice (still Puck), conversation prompt or task history, and the microphone remained off. The output path received PCM and completed playback without error; this establishes real remote generation and device-output execution, not a human judgment of timbre or speaker quality. Inspected `/home/maslow/Pictures/screenshot-2026-09-22_10-59-50.png` shows the real Zephyr preview's Playing/Stop state. Evidence: `preview-check.json`, `preview-stop-check.json`, and `install.log` in `voice-mvp-build/rollout-0.1.5-14/`. Temporary bounded helpers: `/tmp/check-installed-voice-preview.py` and `/tmp/check-installed-preview-stop.py`.

Settings remains open for the user. Select a voice, press Play preview, and press Use this voice to save it. Edit the conversation prompt and press Save prompt; start a new conversation to hear the style. No public release, push/merge, ISO rebuild, account changes or agent permission changes occurred. Earlier rollback archives remain retained. Next action: user listening comparison and a normal conversation with their chosen voice/prompt.


## Reported conversational silence and live retry

After installation the user reported that Zephyr answered initially but went silent when they wanted ordinary conversation without tasks. The earlier rollout tested preview playback, not a full microphone conversation; that coverage gap was explicitly acknowledged. The saved prompt was still the original default, the saved voice was Zephyr, and the provider model was unchanged. Comparison with installed predecessor source showed no microphone/playback implementation change and identical default conversation instructions. These facts do not establish the cause of the silence.

Bounded investigation used the installed production service and existing account. Three successive typed conversational turns, starting with the user's no-task/testing wording, each received an appropriate reply without creating a task. A separate 55-second physical microphone diagnostic received “Hello” and the user's no-task conversation request, generated the corresponding replies, and returned to listening with no recorded error. The user confirmed: “it did answer and i was able to have a follow up conversation.” The diagnostic explicitly ended Voice afterward. No source fix, settings change, account change, service restart or rollback was applied during this investigation.

Private local evidence is under `voice-mvp-build/conversation-regression/`: `typed.json` and `microphone.json`; do not commit these conversation traces. Helpers are `/tmp/voice-conversation-check.py` and `/tmp/voice-microphone-check.py`. Existing audit records are redacted and ended sessions clear the in-memory transcript, so the original missing turn could not be recovered. No claim that the intermittent issue is fixed or that all 30 voices passed. Next action if silence recurs: inspect the still-open session before ending/restarting Voice, capturing whether the user turn arrived, whether an assistant reply was generated, and whether playback completed.


## Long-tangent failure and inactivity correction

The user narrowed the silence report to long spoken tangents. Inspection found a concrete defect in the existing September 19 inactivity policy: only completed assistant turns renewed the 60-second idle deadline. Sustained microphone input and recognized user turns were deliberately ignored, so an ongoing monologue could be disconnected before the final transcript/reply. Recent audit sessions ended approximately 60–61 seconds after their last reply, consistent with this mechanism, though the original lost speech was not retained.

Runtime `d358ded903e60d2b3d2a1b3e74b4f1a724f170ee` corrects the activity accounting. Recognized user input with microphone enabled renews the deadline. Sustained post-APM microphone energy (RMS at least 0.005 for 0.2 seconds, with no sampled gap above 0.3 seconds) also renews it before transcription. Isolated peaks, low-level noise, muted input and input during output speech do not. The 30-minute hard limit and lock shutdown remain. This deliberately replaces the earlier assistant-only policy and its test; it is not a timeout increase. Sustained background noise can extend a session too, because this bounded activity heuristic is not a speech classifier.

The pinned suite passed 340 tests with two expected skips, including a simulated 90-second input turn with no transcript, subsequent quiet expiration, isolated clicks, mute/output rejection, recognized input and hard-cap coverage. UI/controller/orb checks and package invariants passed. Source/model/prompt/voice selections are unchanged beyond inactivity bookkeeping. This simulated time test is not physical acceptance.

Recipe `85781718db8022831457814c993a5c6c05393a6c` builds `0.1.5-15`; archive `voice-mvp-build/voice-long-turn/maslow-voice-0.1.5-15-x86_64.pkg.tar.zst`, SHA-256 `dabc4e3c11db7b247d59ada5d361d94e13fad9ead179d7c5fa1911834574b3ab`. All 44 archive source files, versioned entry points and compiled shader verified. Normal package build/check stages passed; log `voice-mvp-build/voice-long-turn-build.log`. Builder stopped before audio testing; previous packages retained. Rollout is awaiting OS authentication at this checkpoint; evidence directory `voice-mvp-build/rollout-0.1.5-15/`. Next: finish installation and verify a real long spoken turn across the former one-minute deadline.


## User-selected normal and extended conversation modes

The user explicitly preferred keeping the original 60-second safety cutoff and selecting a longer session through a separate shortcut. This supersedes the automatic microphone-activity renewal in `0.1.5-15` (which had installed successfully before this request). Runtime `6962e536` restores the original default policy and adds session-only extended mode. Normal Voice is Super+Shift+V; extended Voice is Super+Ctrl+Shift+V. Pressing the same mode's shortcut again ends Voice. Pressing the other shortcut changes the mode in the existing session without losing the conversation. Extended mode skips inactivity expiration, but keeps desktop-lock shutdown and the 30-minute maximum. Ending Voice clears the flag; no persistent timeout or provider preference changes.

The launcher accepts `start` and `extended`, performs the existing unlock/plugin checks, and uses a serialized daemon toggle. Existing page-launch arguments remain supported. The UI visibly labels extended mode and its maximum. Source defaults include both configurable shortcuts. The installed protected core did not have a live Voice shortcut; Lenovo user bindings use the package-owned `/usr/lib/maslow-voice/launch`, with backup `~/.config/hypr/bindings.lua.before-voice-modes-20260922`. Super+V paste and Super+Ctrl+V clipboard remain unchanged. Hyprland reload/configerrors passed.

339 pinned tests passed with two expected skips; focused normal/extended lifecycle tests cover timeout, hard cap, session preservation, stop/reset and invalid input. Launcher tests cover both modes, lock rejection and setup failure routing. CLI, controller/UI/orb, package invariants and whitespace checks passed. Inspected native fixture screenshot `/home/maslow/Pictures/screenshot-2026-09-22_11-55-51.png` shows the extended label and End conversation control.

Recipe `29e2a00` builds `maslow-voice 0.1.5-16`; archive `voice-mvp-build/voice-extended/maslow-voice-0.1.5-16-x86_64.pkg.tar.zst`, SHA-256 `804160c1f61cd13387255c9ddbfaffae32ad221d3e6137b257277771f4401cd2`. Normal makepkg stages passed. The package installed successfully; all 44 runtime/UI files and the launcher match source, and versioned entry points and compiled shader verify. Builder and source preview stopped before live acceptance. Previous package archives remain available. Evidence root: `voice-mvp-build/rollout-0.1.5-16/`.


Installed action acceptance: the normal launcher started microphone capture; extended launcher switched the same session identity; the real Gemini session stayed active for 67 seconds without inactivity shutdown; repeated extended action stopped it; a subsequent normal start had extended=false and repeated normal action stopped it. Test cleanup left microphone off. Inspected installed screenshot `/home/maslow/Pictures/screenshot-2026-09-22_12-01-07.png` shows the extended label after the timeout boundary. Evidence: `shortcut-action-check.json` under the rollout directory. This verifies the registered command targets, not physical key handling: an initial wtype synthetic chord failed to trigger the binding, and a legacy-style Hyprland Lua-dispatch probe was rejected by syntax. Neither is recorded as a passing keyboard test. Both chords are present in the live Hyprland registry with no configuration errors; user physical-key acceptance remains. No claim that a new long spoken tangent was completed in this window. No public push, merge, package publication or ISO rebuild occurred.


## Simplified shortcuts: Super+H and Super+Shift+H

User requested one key plus Super for normal mode and the same key plus Super+Shift for extended mode. Checked the complete live Hyprland binding registry, including keycode bindings: H was free for both modifier combinations. Super+V is universal paste and was preserved. Source defaults and the backed-up Lenovo user bindings now use Super+H for normal Voice and Super+Shift+H for extended Voice. The prior Super+Shift+V and Super+Ctrl+Shift+V Voice assignments were removed; Super+Ctrl+V clipboard remains intact.

Hyprland reload/configerrors passed. Live registry assertions confirm exactly one binding for each new chord, no old Voice V binding, and unchanged paste/clipboard entries. The full source binding-conflict test and default-config test passed, as did whitespace validation. Local backup: `~/.config/hypr/bindings.lua.before-voice-h-shortcuts-20260922`. Voice package remains `0.1.5-16`; no package build or audio/session changes were needed. Mode behavior and safety limits remain as documented above. Physical keypress acceptance remains for the user; registration and command-target checks are distinct from actual hardware key events.
