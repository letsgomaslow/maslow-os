# Maslow Voice Hub 0.3.0 OTA delivery handoff

Date: 2026-09-13

This handoff records the unsigned final Hub 0.3.0 candidate and the completed test-channel update, rollback, corrected reapply, visual and cleanup evidence. It does not authorize signing, publication, branch integration, an ISO rebuild, or a stable-channel claim.

## Current status

- The final Hub candidate corrects the stale 0.2.1 text in What's New. This copy correction is the only change from the initial 0.3.0 candidate exercised on the installed guest.
- The installed guest successfully followed the disposable signed HTTPS path `0.1.3 -> 0.2.1 -> initial 0.3.0` through Hub.
- The explicit terminal action installed Maslow Voice `0.1.2-1` and Hermes `0.21.0-3`, started the Voice service, and left Voice disabled with `ready: false` as expected before provider configuration. The core runtime versions and saved launcher hash remained unchanged, and the existing Quickshell process, PID 1023, remained running. The resulting Voice Settings screen was visually inspected.
- The normal signed test-channel rollback from initial Hub 0.3.0 to 0.2.1 passed. Voice `0.1.2-1`, Hermes `0.21.0-3`, the active Voice service, the unchanged core versions, saved launcher SHA-256 `8361181a5508700a9d68694b05566e59453f37cfdd16f988d58d9124d2efe37c`, and Quickshell PID 1023 were preserved. Private launch settings succeeded, and the test manifest sequence 101 check passed.
- The final corrected 0.3.0 archive applied successfully through the normal updater at `2026-09-13T18:54:43Z`. The final installed state before the later emulator exit was Hub `0.3.0-1`, Voice `0.1.2-1` and Hermes `0.21.0-3`, with the Voice service active and Voice disabled and not ready as expected. Core versions, the saved launcher hash and Quickshell PID 1023 remained unchanged. The installed `Panel.qml` SHA-256 `5e49b871554fdff92c6cf1f5411194d90e84d4a12876ed590d39871856b8d8f7` exactly matches the final source. All observed lock-state flags were false.
- After that state was recorded, the QEMU process exited with code 11, confirming an emulator SIGSEGV. The container recorded no OOM or OOM kill. Rebooting the same preserved overlay reached the branded login, separating the emulator fault from the already completed package transaction. After login and service readiness, the settled Hub screen passed visual inspection: it shows current 0.3.0, corrected Voice copy under What's New 0.3.0, Up to date, the apply/rollback/reapply history, and the grey bottom-right orb. Earlier black and desktop-only frames were unsettled startup frames. The rebooted state reconfirmed the final package and core versions, launcher hash, active Voice service and one Quickshell process, PID 1008, as expected; PID 1023 applies only to the pre-crash session. Voice Settings was already visually proved by the installed Settings capture and `hub-030-final.png`. The immediate post-reboot `voice-030-final-reboot.png` shows only the desktop and grey orb and is not additional Settings proof. See `voice-ota-030/emulator-exit.log`, `voice-ota-030/final-reboot-state.log` and `voice-ota-030/guest/hub-030-settled-visible.png`.
- Cleanup passed: the allow-idle setting was restored with status disabled, the canonical `stop_vm` operation exited 0, the process audit found no live QEMU process, and only the two owned Voice QA containers were stopped.

## Exact final inputs

| Input | Revision or digest |
| --- | --- |
| Maslow runtime source | `dd7dcc40fb1ce028034c89c7a86e529af6af4b9b` |
| Maslow Hub source | `85d5b7af5e39ff29d728ac7b32de741658894055` |
| Maslow package recipes | `5e423aeddea4b5b42d7fbfbe5bd7f85391c10db4` |
| Final Hub archive | `maslow-hub-0.3.0-1-any.pkg.tar.zst` |
| Final Hub archive size | `474751421` bytes |
| Final Hub archive SHA-256 | `debde65343df2a0c6d2ff1305c0bb4e29f35ab08ecc268028d6f492468914d45` |
| Prepared unsigned manifest sequence | `4` |
| Unsigned manifest SHA-256 | `5a58cb57b65782633fe8d43f8ec33f6c5f3ccefd158eb96ab5629f3c87df5ef7` |
| Retained signed catalog sequence | `1` |
| Retained catalog expiry | `2026-09-24T23:56:41Z` |
| Existing public-key fingerprint | `daacaa5aac138710a3950097b29a05abd3f69c9a8efad512321c45f3103d1ee4` |

The final archive is local evidence at `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/voice-ota-030/final-packages/maslow-hub-0.3.0-1-any.pkg.tar.zst`. The candidate preparation and guarded signing inputs are under `/Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-voice-030`. The superseded archive and manifest digests are deliberately rejected by the signing guard.

The explicit Install Voice action uses these separately built optional archives:

| Package | Version | SHA-256 |
| --- | --- | --- |
| `maslow-voice` | `0.1.2-1` | `2c4b5caa693e504ebf0454e000422be5f2d40ea3177dcc1db3ec38a77da82d32` |
| `hermes-agent` | `0.21.0-3` | `2102449c67c188e4a1ebb9771173ebd0ad2688116f458664344f686afb217ab4` |
| `maslow-voice-local` | `0.1.0-2` | `a17d7613b43c040b88cded635a7e3116a22d5813cc35376771c3d259b00d77c8` |

Voice `0.1.2-1` installs its own `/usr/lib/maslow-voice/launch`, copied from the reviewed runtime helper, and Hub invokes this private package-owned launcher. No core command or PATH overlay and no core runtime package replacement was used in this OTA rehearsal. The earlier implementation handoff's runtime-helper overlay proof is separate from this delivery evidence. This packaged private-launcher boundary is implemented by Hub commit `85d5b7af5e39ff29d728ac7b32de741658894055` and package recipe commit `5e423aeddea4b5b42d7fbfbe5bd7f85391c10db4`.

## Verification completed

- Hub source: 119 Python tests passed. Separate UI contract, guided navigation, preservation and recovery checks also passed. The final archive's 14 helper, UI and version files match Hub commit `85d5b7af5e39ff29d728ac7b32de741658894055`; see `voice-ota-030/final-payload-comparison.log`.
- Package recipe checks passed at `5e423aeddea4b5b42d7fbfbe5bd7f85391c10db4`. The outer Hub archive ownership remains within the existing updater allowlist.
- Real Quickshell ran under headless Weston 15 with Pixman software rendering at 1280x800. The Install, Active, and Failed/Resume Voice states were inspected without clipping, overlap, broken wrapping or missing controls. These captures predate the final What's New copy correction, which does not alter the Voice-page layout; see `voice-ota-030/ui/QA.md`, `install-final.png`, `active-final.png` and `failed-resume-final.png`.
- Native update evidence is in `voice-ota-030/installed-hub-030-final.log` and `voice-ota-030/final-installed-state.log`. The inspected `voice-ota-030/guest/hub-030-settled-visible.png` establishes the corrected final Hub screen after reboot, while `voice-ota-030/final-reboot-state.log` reconfirms the installed state and one new Quickshell process. Earlier installed Settings evidence remains valid because the final candidate changes only What's New copy. Canonical guest cleanup passed.
- The final archive bytes and manifest inputs have been hash-verified. The signing helper passed shell syntax validation and its noninteractive guard exits before any private-key access. No private key was opened, and nothing was signed or published.

## Delivery flow

1. On the signing Mac, run the pinned `sign-voice.sh` from an interactive terminal. It verifies the exact source, recipe, archive, manifest and public-key fingerprints, then prompts through OpenSSL exactly twice: once for the new Hub archive and once for manifest sequence 4. It reuses the already signed immutable historical packages and catalog sequence 1.
2. Let the existing Hub release tooling prepare the GitHub delivery and complete its publication dry run. Review the exact immutable release upload and Pages staging promotion, then continue the already authorized preview publication flow; the signing script itself does not publish.
3. From an anonymous environment, fetch the public staging metadata and artifacts, then verify catalog, manifest and package signatures, hashes, sequence 4, retained historical versions, URL and expiry.
4. On the Lenovo, use the existing Hub Updates flow to check and apply 0.3.0. Record the visible version, unchanged core/runtime hold, preserved launcher state and single running Quickshell process, then inspect Voice installation, launch and rollback behavior.

The public baseline was fetched and anonymously reverified on September 13. It remains manifest sequence 3 with immutable Hub 0.1.3, 0.2.0 and 0.2.1 packages. Catalog sequence 1 remains valid through September 24, 2026 at 23:56:41 UTC. Sequence 4 is prepared locally and remains unsigned and unpublished.

## Scope and limitations

- This is a Hub-only OTA. The accepted ISO, core runtime packages and temporary core hold are unchanged.
- Hub rollback changes Hub only. It does not remove optional Maslow Voice or Hermes packages; the native rollback confirmed that both packages and the Voice service remain installed.
- Voice is cloud-first on the accepted base because that base does not include Weston or Ollama. Local mode requires those additional local packages and a selected downloaded model.
- The current evidence covers source behavior, package structure, software-rendered UI, signed disposable-channel update/rollback and installed disabled-state setup. It does not establish live OpenAI or LiveKit audio, physical microphone/speaker behavior, provider latency, or Lenovo production-channel delivery.
- Publication remains a separate explicit action after signing and anonymous verification. This handoff does not change trust enrollment, source remotes, package channels, release assets or GitHub Pages.

## Next action

The native test-channel gate is complete. On the signing Mac, run the pinned command below in an interactive Terminal, enter the existing encrypted-key passphrase at the two OpenSSL prompts, then follow the existing publish, anonymous verification and Lenovo Hub sequence above. This does not establish live-provider audio or physical Lenovo acceptance.

```bash
bash /Users/r.david/.codex/worktrees/43ab/hub-evidence/ota-voice-030/sign-voice.sh
```
