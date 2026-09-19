# Lenovo Voice development handoff

Date: 2026-09-16. Scope: preserve source on GitHub, organize a portable workspace, and record the tester-reported failure. Troubleshooting is deferred by the user. This handoff supersedes the September 14 instruction to install and test; it does not change released bytes.

This handoff predates the Gemini Voice Lab, glass Orb and movable-Orb commits. Its failure report and source-backup table remain historical evidence for the older installed package. Use the [September 19 integration handoff](2026-09-19-gemini-voice-orb-integration.md) for current source and local-package behavior.

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

## GitHub source backup completed

Verified 2026-09-16T13:00:17.357776+00:00. All 12 listed remote branch tips matched their local source commits. The source/docs closeout is `3d5f6d377136e008e5d2722cf0f750c2ebf3a9dc`; the later documentation-only verification commit is available in branch history. This is remote source preservation, not a product merge, package rebuild, new OTA or Lenovo fix.

| Repository | Branch | Verified source commit |
| --- | --- | --- |
| `maslow-os` | `codex/livekit-setup` | `3d5f6d377136e008e5d2722cf0f750c2ebf3a9dc` |
| `maslow-os` | `codex/maslow-voice` | `e7de217d47b5c2ad77b563553378f7efa1e5c19c` |
| `maslow-os` | `codex/maslow-hub` | `c98cf5da9f9ae0785622f838e0afbd298951ff06` |
| `maslow-hub` | `main` | `d809edfdd9849137e2526ed3ebac6392aaa4aa7a` |
| `maslow-hub` | `codex/gpt-live-test-release` | `5c412c77d4bcdebf0a1e2f01bbd740efea182eea` |
| `maslow-hub` | `codex/maslow-voice` | `9e8574b7a7eb28993ac8f07ec8b982406dd689cd` |
| `maslow-os-pkgs` | `codex/linux-live-packages` | `652583d9d463c60acf999a2c5b5946739316544b` |
| `maslow-os-pkgs` | `codex/maslow-voice` | `ce6749530dabcb7e9810d523192cc8a74619b781` |
| `maslow-os-pkgs` | `codex/maslow-hub` | `e4fab062dc6631f1a14aadeb57f0f88b2ee05fff` |
| `maslow-os-iso` | `codex/maslow-hub` | `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb` |
| `maslow-connect` | `codex/maslow-connect-org-control-plane` | `1b79bebab7d7f69b47b5b0958a6f87f1d61d422e` |
| `maslow-releases` | `main` | `f605c57fa2927a44e218d795845e920e31aca2e9` |

Hub previously had no remote heads; its existing local `main` history and two Voice branches are now backed up in the existing private repository. Runtime/package/ISO product branches were not changed. Public distribution was already synchronized and received no new commit. Connect's existing organization/control-plane branch is backed up in its existing repository. No new repository or history rewrite was required.

Validation: six scoped documentation files, 55 local links, six baseline revision checks and two Bash block syntax checks passed; setup commands were not executed on Lenovo. A targeted scan of 844 outgoing source-history blobs found no matching private-key/provider-token patterns, sensitive credential/build filenames, or blobs over 10 MiB. Scope/whitespace checks passed. Luna independently reviewed inventory and documentation; root reviewed and integrated. No builds, VM, cloud audio tests or live troubleshooting ran. Existing unrelated saved-main prototypes and onboarding worktrees were not swept into this Voice closeout.

Lenovo workspace preparation still needs to be run on Lenovo using the linked guide; there is no direct Lenovo connection in this session. The next diagnostic session must begin from the reported failure and confirm installed versions before any code or service change.
