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
