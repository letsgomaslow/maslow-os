# LiveKit installed-system handoff verification

Continuation: [native audio recovery and later package evidence](2026-09-14-livekit-native-audio.md) supersedes the remaining-audio status below; this checkpoint and its original results are preserved.

Status: real typed LiveKit-to-Hermes handoff passed in installed Maslow AI-OS after two source fixes. Spoken handoff and audio quality have not passed. This is an unpublished development checkpoint, not Lenovo readiness.

## Scope and exact candidate

The user requested LiveKit Expressive conversation and task delegation inside Maslow AI-OS before Lenovo testing. This investigation used the existing ISO repository's headless QEMU/TCG installed overlay, SSH for guest commands, and QMP screenshots. No UTM, ISO rebuild, signing, publication, OTA or Lenovo change occurred.

- Current built runtime: `64a794ad4fb289ec2782f916869b1781bd5ad168`, branch `codex/livekit-setup`.
- Current package recipes: `09347b3fedc551cf83f0e80779184cd6daae87eb`, branch `codex/linux-live-packages`.
- Installed candidate: `maslow-voice-0.1.4-11-x86_64.pkg.tar.zst`, SHA-256 `037f02fe887e1ec7fe14daf11cf00308ee03741da9c94893e9dcc45352d5b2e8`. Hub 0.3.1-1 and Hermes 0.21.0-3 were installed in the guest.
- Reused September 8 installed overlay from ISO SHA-256 `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`; this is not a fresh installation check. The [native integration handoff](2026-09-13-gpt-live-native-integration.md) records earlier installed checks.
- ISO harness checkout: `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb`; copied base-test SHA-256 `7c6f15de64722c877dfdb8cb662b8e8f0b0aa7b80d8633fc5d82b1eb92240de2`.
- Actual guest: Arch x86_64, Python 3.14.7, LiveKit RTC 1.1.18, Agents 1.8.1, LiveKit API 1.2.1, Silero plugin 1.8.1, sounddevice 0.5.6. Configured voice Olivia, Expressive enabled; Hermes used the existing native cloud execution profile.
- Initial VM: four virtual CPUs and 2 GiB RAM. Later profiles and final package checks used eight virtual CPUs and the same RAM. No production audio buffers or deadlines were changed to compensate for emulation.

The starting package was Voice 0.1.4-9, SHA-256 `4b465a4cff46e4da6a5bf549d9fefcabd0f70fa312dedd76a1219a29136228ab`, runtime `675019e524759f0ab66a2f8b0079e5aea2d4d9bb`, recipes `3fe0daf7143cc041804a1f8a34560db10b5401fd`. Starting documentation HEAD was `3be3c384bfca90082f8edd5680cebd30f9d83862`. Later documentation commits do not change the built package.

## Verified task handoff

The final typed diagnostic ran the installed VoiceService and real LiveKit model function tool, with audio disabled. It sent an ordinary typed request through the conversation. It did not inject an intent or submit a task directly. The production coordinator started on the first real task, without prewarming.

- The real LiveKit `submit_intent` callback selected the allowed `hermes` preference and created exactly one task through the normal host validator.
- Task `e59471bb-6057-498f-a568-cb975a3caab4` progressed from queued to submitting, accepted, running and completed. Hermes run identity: `run_4579d63d0c054118be16365c71c56a77`.
- Stored source exactly matched the captured request; provider mode and project matched. The project was `/home/omarchy/livekit-native-qa/text-project`.
- Hermes created the exact requested `result.html`, 493 bytes, SHA-256 `50d3877ddf50749e96f7c1bdbe0b00c08e26d501d26f324b282b73150b2cadcb`. Its H1 contained “Weekend hiking checklist” with green styling and the requested water, snacks, rain and first-aid checklist terms.
- A separate packing question received a relevant final assistant reply while the task was accepted and before it completed. Only one normal submit callback and one new task were observed. There were zero provider errors. The normal `end_voice` request returned, then service SIGTERM cleanup completed; the audio-disabled microphone-off flag by itself does not prove provider shutdown.

Measured times from scenario start: LiveKit listening 59.4 seconds; task queued 63.8; submitting 176.0; accepted 182.6; follow-up reply 186.4; running 220.6; completed 272.9. These are emulator measurements, not expected laptop performance. The interval before submitting was about 112 seconds; cold startup during real audio still needs acceptance.

This proves the installed provider's text-to-tool-to-Hermes path and independent typed conversation. It does not prove speech recognition, continuous spoken conversation, native speaker quality, voice UX or physical laptop behavior.

## Confirmed defects and fixes

### Python 3.14 schema construction

The initial real typed attempt reached listening, then emitted `LIVEKIT_SESSION_FAILED` before inference. A safe SDK observer captured `LLMError → APIConnectionError → KeyError`. Offline reproduction with the pinned dependencies resolved this to `KeyError("context")` in strict function-schema construction on Python 3.14. Python 3.13 constructed the same schema successfully.

The provider mutated a function's annotations in place. Python 3.14's lazy annotation callback, copied by the SDK wrapper, regenerated the original annotations and omitted the injected context type. Runtime commit `12265b64879e2dfbf6877eae437d85cefa70419f` assigns a complete mapping and synchronizes the lazy callback before decoration. It changes neither the model-visible tool fields nor provider dependencies. Regression coverage calls the actual pinned `ToolContext.parse_function_tools("openai", strict=True)`, verifies all six fields, excludes injected context, and rejects additional properties.

This was packaged as Voice 0.1.4-10 with recipe `e35cd5379ec8de7dfadd967c87afa335ae56a4d4`, SHA-256 `6b9f990949764e049312683a083a4f7deab2874fed9609de51272885f7545544`, then installed normally in the existing guest.

### Unsupported tool choice and misleading acknowledgment

After that fix, the real model replied without a provider error but supplied a `tool_preference` outside the host's four supported values. Safe observer metadata established that the other field types, text, list contents, provider state and captured turn were valid. The model-facing schema had advertised unrestricted text. The host correctly rejected the request, but the assistant misleadingly promised to start work even though no task existed.

Runtime commit `64a794ad4fb289ec2782f916869b1781bd5ad168` uses the existing `ToolPreference` type to expose the existing `auto`, `codex`, `claude` and `hermes` enum in the strict schema. Tool responses distinguish `SUBMITTED` from `NOT_SUBMITTED`, with instructions to acknowledge rejection truthfully. The host validator still rejects unsupported choices. This strengthens model guidance; it cannot guarantee that a model never misstates status. The successful package-11 retest is recorded above. No dependency or executable capability was added.

The first package-10 typed helper also incorrectly interpreted `voice.enabled == false` as session closure, although `audio=False` intentionally leaves that field false. The helper was corrected to check provider liveness and microphone state. Its invalid-assertion result is retained separately. The later rejected-intent attempts were stopped with normal `end_voice`; they did not spontaneously disconnect. The schema error diagnostic's `passed: true` means failure capture worked, not that provider acceptance passed.

## Spoken audio results

The spoken scenario feeds public synthetic speech into a PipeWire virtual microphone, then the installed PortAudio/APM/LiveKit path. The model must hear the request, invoke the real constrained tool, and cause Hermes to create the exact file. A second spoken question must receive a relevant transcript and audible reply while work is active, followed by 60 seconds of live audio. Synthetic intent injection or typed correction cannot pass this test.

| Check | Observed result | Evidence boundary |
| --- | --- | --- |
| Saved LiveKit connection | Regular URL/key/secret setup accepted; listening state and microphone on | Setup and room connection passed; this alone does not prove inference or execution |
| Original spoken attempt, four CPUs | Severe capture loss, no final user transcript, no tool, no task, no non-silent returned audio | Root requested normal shutdown after observing loss; not spontaneous closure |
| Ten-second intake, four CPUs, desktop running | 36 forwarded frames, 396 dropped | Failed before speech injection |
| Same profile, owned compositor and shell paused | 458 forwarded, 41 dropped | Improved, still failed; not visible-desktop acceptance |
| Eight CPUs, desktop running | 36 forwarded, 401 dropped | More virtual CPUs did not fix loss |
| Eight CPUs, normal reduced motion and 1024×768 at 60 Hz | 33 forwarded, 397 dropped | Smaller display and reduced motion did not fix loss |
| Package 11, eight CPUs, graphics paused, 15-second warmup plus settling | 711 forwarded and 30 drops during warmup; queue did not remain drained during the next 15 seconds | `SILENT_INTAKE_DID_NOT_SETTLE`; no speech injected, no task; normal shutdown and automatic graphics resume |

The ten-second intake gate requires at least 45 forwarded 20 ms frames per second and no more than ten drops. All four profiles failed. The later strict scenario also preserves its drained-queue settling gate. No production buffer or test threshold was relaxed.

Pausing graphics reduced median `capture_frame` latency from 153.6 ms to 8.3 ms and event-loop lag from 295.6 ms to 14.6 ms in the four-CPU comparison. A bare RTC AudioSource benchmark measured 3.27 ms median and 9.55 ms p95, but excluded the published room, native audio and full inference pipeline. These results implicate emulated rendering contention without fully explaining every loss; they do not establish a Lenovo defect. Hyprland v0.56.2 reported default `debug:vfr=true`, `debug:damage_tracking=2` and `debug:damage_blink=false`, with no explicit overrides. No saved forced-render setting was established.

The separate functional-only spoken diagnostic also failed. It embedded the earlier failed quality result and hash, retained `passed: false` and `overall_passed: false`, and reported `functional_passed: false`. Warmup dropped 72 packets; after the request, total drops reached 541. LiveKit produced two final user turns, “Please ask Hermes to create a name result on page” and “of”, instead of the complete fixture. Its final reply said no work had been submitted and asked for clarification. No host submit callback, task or artifact was observed. Returned playback did reach the virtual speaker monitor (308,516 samples above the diagnostic threshold), but this is not evidence of audible quality.

Root then requested normal `end_voice` after the diagnostic question was answered. The resulting `VOICE_ENDED_BEFORE_ACCEPTANCE` at 335.9 seconds is operator-initiated, not spontaneous disconnection, idle expiry or timeout. Service cleanup completed and the wrapper resumed graphics. No concurrent spoken follow-up or post-task soak was reached. The retained transcript and explicit operator-stop file explain this boundary; the unchanged quality gate remains failed.

An eight-CPU boot stalled before SSH once, then succeeded unchanged. The focused Sign in button required Space; Return/click attempts had not authenticated. The normal Voice launcher deferred on the busy desktop. QMP inspection showed the actual Hub desktop and orb, but not an open Voice conversation panel. No UI changes were made this turn; the earlier Docker/Weston visual evidence does not replace this remaining installed interaction gate.

## Checks and local evidence

- At annotation fix 12265b64, Python 3.14.4 full Voice suite: 207 tests, 205 passed and two platform skips; UI contracts passed. All 15 LiveKit startup/schema tests passed separately on Python 3.14.4 and 3.13.13.
- Installed package 10, Python 3.14.7: all 15 startup/schema tests passed in 56.569 seconds.
- After enum/acknowledgment fix 64a794ad, three focused regressions passed on Python 3.14.4, Python 3.13.13 and installed Python 3.14.7 (52.411 seconds in guest). They exercise real strict-schema enum generation, rejection without submission, and captured-turn binding across later input/interruption. The full 207-test suite was not rerun after this focused change.
- Both package revisions passed shell syntax and package invariant checks, built successfully and installed normally. Package 11 then passed the real typed handoff described above. A post-test guest read confirmed version 0.1.4-11 and provider-file SHA-256 `883b0ca22225b0adbccfd250a4522ef4e0538d5656bad002ef2dae27f9e91478`, matching the committed runtime source.

Evidence root: `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/livekit-native-acceptance/`. These machine-local files are not committed or published.

- `provenance.json`, `installed-preflight.json`: source/package/SDK provenance and non-secret presence checks.
- `text-cold-handoff-revision11-result.json`, matching log, `typed-task-trace.json`: completed real handoff, captured source checks, concurrent typed reply and real Hermes run identity.
- `first-run/result.json`, four `profile-*.json` files, `native-paused-revision11-result.json`: failed spoken/intake evidence, preserved independently.
- `native-functional-revision11-result.json`, `functional-transcript-diagnostic.json`, `functional-operator-stop.json`: failed functional-only speech diagnostic, redacted synthetic transcript and explicit normal-stop annotation.
- `typed-result.html`, `post-test-installed-verification.log`: retrieved synthetic artifact and guest package/provider hash confirmation.
- `text-handoff-result.json`, `text-error-diagnostic-result.json`, package-10 failed results: schema failure, safe cause-chain capture, invalid helper assertion and rejected tool-choice traces. Operator stops remain explicitly annotated.
- `python314-suite.log`, `install-revision10.log`, `install-revision11.log`: exact test scope above.
- `../linux-live-acceptance/build/revision10/` and `revision11/`: package archives, inputs, build logs and provenance.
- `livekit-native-scenario.py`, `livekit-native-paused-scenario.py`, `livekit-native-functional-diagnostic.py`, `livekit-audio-profile.py` and text helpers: distinct scoped scenarios and observers; not production substitutes.
- `audio/request.wav` and `audio/follow-up.wav`: public synthetic fixtures; hashes/durations in provenance.
- `../linux-live-acceptance/installed/guest/livekit-reduced-display.png`: inspected QMP desktop at the reduced QA resolution.

## Cleanup and remaining gates

Guest cleanup passed. A bounded exact-value scan of 4,936 regular files under owned QA directories and Voice state found zero credential matches; 22 files larger than 32 MiB were skipped. This is not a whole-disk scan. All three guest keyring values were removed and rechecked absent, and the Hermes RAM environment file was removed. Voice/OS motion settings and the original display mode were restored, compositor/shell were confirmed resumed, the temporary Voice unit mask was removed and the unit stopped. The existing harness stopped the owned VM, and both owned installed/build containers were confirmed stopped. All three private Mac tester pages still responded afterward.

Credentials were transferred from the already authorized private Mac testers without printing values. Guest Secret Service and Hermes profile were held on tmpfs, with disk swap disabled; logs expose allowlisted diagnostic fields and redacted synthetic QA transcripts. The Mac testers on ports 57517, 57518 and 57519 were preserved. Cleanup evidence is `credential-cleanup-result.json`, `restore-display-result.json`, `service-cleanup.log`, `vm-stop.log`, `vm-stopped-verification.log`, `owned-container-state.log` and `mac-testers-preserved.json`.

The independent evidence review confirmed the typed tool path had no intent/task injection. It also identified limits: follow-up checks use event order and broad keywords, so the captured relevant typed reply is necessary corroboration; a future spoken pass must inspect the actual synthetic question and reply. One observed callback is not an exhaustive claim about out-of-band tasks, and HTML source checks do not prove browser rendering.

Before Lenovo delivery, obtain a passing spoken file-creation and concurrent spoken follow-up run with the desktop active, exact filename/content checks, non-silent returned audio and the unchanged intake gate. Resolve the emulator scheduling/audio loss or establish a faithful accelerated x86 test environment; repeated equivalent TCG retries are not additional acceptance. Physical microphone/speaker quality and echo cancellation, cold coordinator startup during speech, the installed conversation panel, and Lenovo acceptance remain open.

LiveKit still has no production task-progress relay into the conversation; native Tasks remains authoritative for execution status. Direct Codex/Claude launches and local-only inference are separate open gates. The earlier GPT-Live filename failure remains open in its own handoff. Published staging sequence 4 / Hub 0.3.0 and frozen unsigned Hub 0.3.1 / Voice 0.1.3 artifacts remain unchanged. Nothing in these local results authorizes release promotion.
