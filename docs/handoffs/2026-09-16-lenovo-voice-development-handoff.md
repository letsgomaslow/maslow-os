# Lenovo Voice development handoff

Date: 2026-09-16. Scope: preserve source on GitHub, organize a portable workspace, and record the tester-reported failure. Troubleshooting is deferred by the user. This handoff supersedes the September 14 instruction to install and test; it does not change released bytes.

## Current result and evidence boundary

The user reports completing the Voice update on Lenovo, saving the GPT-Live OpenAI key, and properly setting up Hermes, but says it is not working. Update arrival and setup completion are tester-reported. Exact installed versions, the visible error, microphone behavior, provider connection, and whether conversation or task execution fails have not been collected. Do not describe Hermes as independently verified or infer an authentication, audio, networking, or routing root cause.

| Gate | Status |
| --- | --- |
| Hub 0.3.2 / Voice 0.1.4-9 signed publication | Passed September 14; immutable release and staging sequence 5 anonymously verified |
| Lenovo Voice update arrival | User-reported completed September 16; exact installed versions not yet inspected |
| OpenAI key and Hermes setup | User-reported completed; runtime readiness not independently verified |
| Lenovo usable Voice / GPT-Live end to end | Failed user acceptance: “not working”; failing layer and cause unknown |
| LiveKit | PENDING; preserve experiments, do not resume automatically |
| New troubleshooting or fix in this session | None; documentation/source backup only |

Retain the [release record](2026-09-14-gpt-live-lenovo-test-release.md), [consolidated accomplishments and RCAs](2026-09-14-voice-checkpoint.md), and [native GPT-Live evidence](2026-09-13-gpt-live-native-integration.md). Prior emulated and Mac passes remain valid only at their recorded scope; they did not establish Lenovo readiness. No new ISO, provider test, model download, package change, or stable-channel promotion follows from this handoff.

## Development on Lenovo

Use the [repository map and workspace setup](../lenovo-development.md). Voice belongs to `maslow-os/voice/`; a new Voice repository is unnecessary. Clone development repositories alongside each other, outside the installed runtime. Keep the shipped source in a separate pinned worktree for diagnosis: current integration includes unpublished LiveKit changes and is not the package installed on Lenovo.

GitHub source backup is distinct from merging into product branches or delivering an OTA. The user authorized source commits and pushes in this session. Preserve public/product branches and exact release artifacts; do not force-push, flatten history, or commit unrelated concepts, private logs, credentials, or build outputs. Connect remains independently owned and is not a prerequisite to establish the current Voice-to-Hermes path.

The Git history and this repository's documentation are portable. Existing PNGs, VM overlays, package archives, raw traces and RAM-only Mac test credentials are local evidence, not a portable test environment. Reconstruct tests using recorded pins and existing harnesses when needed; never copy signing keys or credential stores into the development workspace.

## Next diagnostic session

1. Confirm installed Hub, Voice and Hermes versions and the exact source/package relationship before changing anything.
2. Ask which failure occurs: opening Voice, starting the microphone, connecting/talking, or handing a task to Hermes; capture the displayed safe error and time.
3. Inspect the user service, Secret Service availability, audio device selection and reduced readiness snapshot through the existing interfaces. OpenAI and Hermes authentication are separate checks. Do not dump credential stores, raw environment values, or unrestricted logs into Git/chat.
4. Reproduce conversation alone, then a typed disposable-project task, then a spoken task. Keep provider audio, brief accuracy and actual task artifacts as separate gates.
5. Change only the owning source after identifying the failing layer; verify locally on Lenovo plus focused regression checks. Use Docker/Weston for visual iteration and the ISO's QEMU/TCG/CIDATA/SSH/QMP harness for installed-system regression proof. No UTM.
6. If running source against the packaged virtual environment, explicitly document source revision, environment/lock compatibility, daemon ownership and how to restore the packaged service. Do not set a global `OMARCHY_PATH`, overwrite `/usr/lib/maslow-voice`, reset settings, or silently run two daemons as a shortcut.

## Lessons and RCA status

Confirmed lesson: package delivery and successful emulated/Mac checks are insufficient hardware acceptance. Track update arrival separately from working conversation and downstream execution. The present failure has no confirmed RCA; all candidate causes remain hypotheses until evidence is collected. Preserve original failed attempts rather than replacing them with a later passing summary.

The default macOS Git launcher refused this session because of an unaccepted Xcode license. The installed Command Line Tools Git binary worked directly, allowing normal source operations without changing system settings or accepting a license on the user's behalf. This host-tool issue is unrelated to Lenovo Voice.

Documentation-only validation covers local links, referenced revisions, whitespace, staged scope and remote branch equality. Builds and paid provider sessions are not rerun for documentation edits. Source-backup results are recorded in the development index; device troubleshooting remains the next session's work.
