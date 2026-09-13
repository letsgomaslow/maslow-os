# LiveKit setup correction and Hub 0.3.1

The user reports that the published Hub update and Voice module are visible on Lenovo. This establishes tester-reported arrival and visibility, not a LiveKit account conversation. They asked for exact LiveKit account setup and challenged the earlier testing claim. We explicitly corrected it: installation, interface and update checks did not include live LiveKit inference or physical audio.

## Confirmed defects and scoped correction

Review against the installed LiveKit Agents 1.8.1 / RTC 1.1.18 SDK found three concrete Voice 0.1.2 defects: lazy STT/TTS streams required an HTTP session that was absent outside LiveKit's worker context; the microphone track was published with the default unknown source instead of microphone; and incoming audio used an integer enum that the string comparison rejected. Voice 0.1.3 supplies and closes its own HTTP session, closes caller-owned inference clients, publishes the correct microphone source, routes the actual audio enum and cleans up failed or cancelled startup.

Cloud readiness copy now says **Check setup** and explains that **Start talking** tests connection and audio. Its underlying check still only checks local prerequisites and saved fields. It does not authenticate the account, verify inference quota, or test a microphone/speaker.

Hub 0.3.1 compares installed cloud-component versions with its bundled manifest without hashing/extracting archives during status polling. **Update Voice** reuses the existing explicit terminal installer. Hub apply does not automatically install Voice, and an equal/newer installed Voice does not receive a downgrade action. Hermes and local-support archives are unchanged.

## Exact build inputs and artifacts

- Runtime: `0a7410b48b4f4d400dd618ec0d3e95c3b471d91b`.
- Hub: `9e8574b7a7eb28993ac8f07ec8b982406dd689cd`, version 0.3.1.
- Package recipes: `ce6749530dabcb7e9810d523192cc8a74619b781`.
- Voice 0.1.3-1: 284,610,614 bytes, SHA-256 `7a91ab5bc6155be8a647cdae3f976eea28bb7854e04d0f754a8fde69527616f9`.
- Hub 0.3.1-1: 474,676,595 bytes, SHA-256 `31a7958d89ec26a4eb13194ff5ac011dccaaaaba4a281ee4e4a529fe48c2af48`.
- Unsigned staging sequence 5 manifest: SHA-256 `e79d39733f8d92bf8e7945c7510b5414853fc11ee5279fdcaa03febc937247a8`.
- Catalog sequence 1 and all four published Hub versions/signatures are retained. Metadata expiry remains September 24, 2026 at 23:56:41 UTC.
- Existing ISO, core runtime package, settings package and trust are unchanged. Source commits are local and unmerged.

## Verification and limits

- Full Voice suite passed on macOS and the x86 Linux builder: 105 tests, two namespace tests skipped in each environment. Six new SDK regressions cover standalone startup, lazy HTTP acquisition, actual enums/options, failed/cancelled startup and cleanup. HTTP calls are forbidden by these tests; they are not live-account proof.
- Hub worker ran `release/check.sh`: 124 tests and all three UI contract groups passed. The root reviewed the changes. Package invariants, recipe syntax, UI contract and whitespace checks passed.
- Built Voice and Hub archive ownership and modes were audited. Patched provider/QML bytes match source. All three nested archives match the bundle manifest. A fakeroot warning during the Voice build did not translate into incorrect owners or modes in the resulting archive.
- The build container initially lacked runtime packages; they were installed before rebuilding. Pacman's download sandbox is unsupported under this container's emulation, so only the container download step used `--disable-sandbox`; package signature and integrity verification stayed enabled. No Lenovo package-manager configuration changed.
- Real Quickshell under headless Weston at 1280×800 passed the fresh-install, current-version and available-update states. Root inspected the Update Voice capture. See the evidence directory below.
- Voice Settings also passed real Quickshell under Sway/Weston software rendering at 1280×800. The LiveKit field layout and the full new cloud setup explanation were inspected without clipping or truncation. Evidence: `ui/voice-livekit-settings.png` and `ui/voice-livekit-settings-final.png`.
- The existing QEMU overlay took several minutes to boot. The non-LUKS/resume warnings were not the final stop location: it reached SSH and login without reset, disk change or reprovisioning. Installed upgrade proof is recorded at the next checkpoint below.
- Actual installed desktop keyring roundtrip passed under the user session: both LiveKit slots were first confirmed empty, synthetic values were saved and read back, then deleted and confirmed empty again. No unlock prompt was needed in this guest. Values were not printed, and no LiveKit connection was attempted. Evidence: `keyring-roundtrip.log` and `keyring-check.py`.
- Live LiveKit authentication, available inference usage, physical microphone, audible reply, interruption and end-conversation acceptance remain open. Do not describe this patch as a successful LiveKit conversation.

## Evidence and next step

Installed correction checkpoint: normal signed test-channel Hub GUI apply completed `0.3.0-1 → 0.3.1-1`. The settled Hub page showed the new **Update Voice** action, and clicking it launched the existing branded terminal with its normal sudo step. That installer upgraded only `maslow-voice 0.1.2-1 → 0.1.3-1`; Hermes remained `0.21.0-3`. The Voice setup stage is complete and its user service is active. The root compared the before/after preservation JSON: saved Voice settings, task database contents, saved launcher, private launcher, held core versions/core launcher and shell PID 1283 all match exactly. No trust change, direct package-install shortcut or core-runtime update was used. Package checks ran in both unprivileged preflight and root staging; TCG made this slow. The duplicate apply was rejected with `UPDATE_BUSY` while the original transaction continued. The initial `voice-update-before.png` is an unsettled desktop frame, not UI proof; use `voice-update-ready.png` and `voice-install-progress.png`, both inspected by the root. Rollback was not repeated for this patch; the previous same updater path has recorded rollback/reapply coverage, and this run verifies the new optional Voice upgrade path.

Final installed SDK smoke passed one real-SDK startup/lazy-session/cleanup regression with HTTP blocked, using the installed package; it took 70 seconds under TCG. The installed provider's SHA-256 matches the corrected source. Voice Settings opened in the same desktop shell and was inspected in `voice-settings-settled.png`. This completes installed correction proof, not live LiveKit authentication or audio acceptance.

Build/visual/guest evidence: `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/voice-ota-031/`. Existing VM and test trust remain under `voice-ota-030/`; the disposable test channel advances to sequence 102 and is not public release trust.

Release preparation: `/Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-voice-031/`. `current-public/verification.json` freshly verifies public sequence 4 and all four immutable archives anonymously. `candidate-sequence-5/` contains the unsigned candidate. The replacement `sign-voice.sh` pins the build inputs, artifact bytes, retained signatures/catalog and existing public fingerprint, then prompts the operator twice. It signs only the new Hub archive and manifest. No protected private key or passphrase was read by the agent.

Installed verification is complete. Allow-idle was restored and canonical `stop_vm` returned 0 with no remaining QEMU pidfile; the preserved overlay remains available. Do not rerun the completed 0.3.0 signing script. The operator runs the new script in Mac Terminal, enters the existing passphrase twice, and replies done. Continue the established verified-artifact publication and live-metadata verification flow from the [0.3.0 OTA handoff](2026-09-13-maslow-voice-ota-delivery.md). No new ISO or trust bootstrap is needed.

The exact account/field mapping is in [First LiveKit Expressive conversation](../maslow-voice.md#first-livekit-expressive-conversation). Maslow already runs its agent locally, so no separate LiveKit Cloud agent deployment is needed. Project URL, API key and API secret suffice; Expressive Mode is enabled by code using supported Inworld TTS 2 / Ashley through LiveKit Inference.

## Queued Lenovo appearance issue

The user supplied `PXL_20260913_201521157.MP.jpg` showing a flat pale Voice circle with the microphone off. A muted disabled state is expected, but the photo does not establish the desired depth or Maslow branding, nor does it prove a hardware limitation. The user explicitly requested LiveKit test instructions first and investigation of this appearance afterwards. Preserve the photo at `/Users/r.david/Downloads/PXL_20260913_201521157.MP.jpg`; do not treat this patch as resolving orb appearance.

After providing the account/field instructions, a focused source inspection found `VoiceOrb.frag` replaces its entire colour with constant `vec3(0.42)` when disabled. This removes the shader's shading, providing a concrete code cause for a flat disabled disc. The active shader is also a simple two-colour mix; it does not implement the richer orb discussed in the concept. The photo does not identify the actual Lenovo renderer or prove that path was active, but no hardware limitation has been established. Follow-up should preserve depth and recognisable Maslow character in the muted state and inspect each state on Lenovo; do not silently change this already-built correction's bytes.

The software path retains the `VoiceOrb.qml` grey gradient, while its loader enables the flat disabled GPU shader only when the graphics API is not Software. This code-level mismatch explains why software preview alone did not cover the GPU appearance. Verify both render paths and their disabled/idle/listening/speaking/working states in the follow-up. The differing code is confirmed; the Lenovo's actual graphics backend remains to be measured.
