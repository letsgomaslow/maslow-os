# Maslow Voice native verification checkpoint

The user asked for verification inside Maslow AI-OS before another Lenovo test. This checkpoint separates current native source checks from the successful private Mac conversation experiment. GPT-Live remains absent from the production provider factory and native settings. The full GPT-Live conversation-to-selected-agent experience has not been proved inside Linux.

## Exact source and evidence

- Runtime and UI tested: `d5aee266093e4b1e86bc53a8ecc4634ec1d11cbf`, active worktree `/Users/r.david/.codex/worktrees/maslow-voice/livekit-runtime`, branch `codex/livekit-setup`.
- Portable cancellation test correction: `34661948`; production runtime/UI are unchanged by this commit.
- Evidence root: `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/native-voice-verification/`.
- A Luna worker audited prior evidence and production selection. A Terra worker ran the native preview and corrected the bounded test fixture; the coordinator reviewed the change and ran the installed guest. No token-cost measurement was made.

## Fast native rendering

The exact requested route is recorded in `docker/weston-nested/HANDOFF.md` and `results.json`: Docker image `maslow-hub-ui-qa:local`, Weston 15.0.1 headless/Pixman on `wayland-weston`, Sway 1.12 with `WLR_BACKENDS=wayland` hosted on Weston, then Quickshell 0.3.1 with software rendering on Sway's layer-shell output. `swaymsg` verified active `WL-1` at 1280x800. Sway supplies the layer-shell protocol that Weston itself lacks.

Inspected PNGs show disabled at bottom right (56px), listening at bottom center (88px), and outstanding tasks at bottom left (56px). LiveKit's three placeholder-only setup fields and Save control are readable. Two speaking frames have distinct hashes. Controller states are fixtures; this is real QML rendering and interaction, not a provider or microphone conversation.

The first preview ran Sway with its own headless output while Weston ran separately. Its records were corrected to state that exact topology, then the Weston-nested route above was run independently. The initial preview additionally covers all four settings modes and records a keyboard Stop action as `end_voice`. Its Mesa/OpenGL screenshots reproduce the disabled shader's flat grey disc; the software fallback retains a gradient. The earlier Lenovo photo has the same appearance, but the physical Lenovo renderer has not been identified. The orb design defect remains unfixed.

## Installed x86_64 environment and source tests

The reused ISO harness is `test/integration.d/base-test.sh` from installer commit `d96a3ee563df5a1eb76a711c7b408c0d1d0137cb`; its SHA-256 `7c6f15de64722c877dfdb8cb662b8e8f0b0aa7b80d8633fc5d82b1eb92240de2` matches the copy used in the guest container.

The original CIDATA/SSH-installed baseline is the preserved September 8 internal sizing ISO `maslow-os-2026.09.08-x86_64-hub-0.1.3-sizing-local-internal.iso`, recorded SHA-256 `c3ee08889eaa50bf2843ae6d0bdc45f8549569f956159421b1e67b98a31b363a`. That ISO was not rebuilt or rehashed during this checkpoint. A new disposable overlay at `installed/guest/run.qcow2` uses the preserved `voice-ota-030/guest/run.qcow2` as its read-only backing image, with separate firmware variables. The previous image, release artifacts and trust material were not modified.

The guest ran QEMU/TCG with two emulated CPUs, 1536 MiB RAM and the existing 64 MiB TCG translation-cache wrapper, with no display window. Guest commands used the harness SSH connection; login, screenshots and OCR used QMP. No UTM keyboard or clipboard was used. This is a reused installed-system overlay, not a new unattended installation.

Verified package baseline: x86_64, Python 3.14.7, Hub 0.3.1-1, Voice 0.1.3-1, Hermes 0.21.0-3. The current Voice source was copied from an exact Git archive into the disposable guest. Hashes matched for the audio engine, LiveKit, OpenAI Realtime, experimental GPT-Live and native panel. The installed Voice virtual environment ran the suite against that source: **177 tests, 175 passed, 2 skipped, zero failures**, in 108.727 seconds. The two skips require the actual Mac sandbox; both real Linux namespace tests passed. Real installed SDK surface/AEC checks, synthetic protocol/lifecycle tests, task-state tests and cancellation tests are separate from any real account conversation.

The initial suite hung at the development scratch executor's cancellation-during-spawn test. It called the Mac-only command builder before signaling its synthetic-child launch, then waited indefinitely. Commit `34661948` patches only the test's command builder, still launches a real synthetic child and asserts it is reaped, and bounds the launch wait. The complete installed suite passed after this correction. The targeted test and all 11 scratch execution tests also passed on the Mac test environment. No assertion was skipped or weakened to pass Linux. The initial incomplete log is retained as `installed/current-source-tests-initial-hang.log`; the successful rerun is `installed/current-source-tests.log`.

## Installed desktop scope and observations

Current production Python modules and QML were overlaid only inside the disposable guest. This is source verification using installed dependencies, not a new package install or an updater acceptance result. The packaged version remains 0.1.3. The unchanged compiled shader was reused. The same Quickshell process, PID 1015, survived the guarded plugin refresh checks; the Voice service was active.

A same-path QML overlay initially displayed the old cached interface despite matching files on disk. That screenshot is retained as `installed/guest/current-voice-settled.png` and must not be presented as current UI proof. The QA entry point was then moved to `qa-d5aee266/Panel.qml` inside the disposable guest to exercise a fresh component path, as a versioned package would. This temporary entry point is not a product metadata or package change.

The new UI was directly inspected in `installed/guest/current-livekit-settings.png`; its `Voice is off` wording, expanded panel and three-field setup distinguish it from the old cached component. QMP selected LiveKit in the running interface, then scrolled to `installed/guest/current-livekit-after-input.png`, which visibly includes Save LiveKit setup, the Ashley selector and Task settings. These are the actual installed desktop and production Voice controller, without preview fixtures. The full-screen OCR wait falsely timed out because its page-segmentation mode could not reliably read the crowded Hub/Voice layout; the retained `failure-waiting-for-voice-settings.png` is the same visually verified frame, not a missing panel. Sparse OCR on the scrolled frame independently detected Ashley and the Voice controls.

Native layout finding: the installed desktop's font metrics put part of Save and the voice selector below the initial visible area at 1280x800, whereas the compact fast preview fits Save. Scrolling works, but the setup action should be easier to find. This UX fix is queued with the flat disabled orb; neither was changed in this verification-only checkpoint. The background Hub view is not a Hub update acceptance check.

The guest took several minutes to boot and printed the previously recorded non-LUKS/resume warnings. It reached SSH and the branded login without a reset or disk repair. `plymouth-start.service` remains the same failed boot-screen unit recorded in the previous guest run; it did not prevent login. The first inventory command also requested Weston, which is absent inside this installed guest; its desktop uses Hyprland. The first shell-open command hit the normal two-second IPC timeout under TCG; the supported `OMARCHY_SHELL_IPC_TIMEOUT=45s` override was used in the test environment. No product timeout was changed.

## Remaining gates and next action

1. Integrate the selected GPT-Live conversation transport with Linux settings, daemon lifecycle and the selected task handoff. Its development adapter is not selectable in production. The Mac scratch backend uses macOS isolation and is not the Linux executor.
2. Fix and inspect the disabled orb on both software and shader paths, and keep the setup action and voice choices easy to reach at the installed desktop font sizing.
3. Run the integrated Linux experience against a real provider account with synthetic input/output and a verified task result while conversation continues; check Stop, cancellation and microphone state. No real account credentials were moved into this guest and no real provider conversation was performed here.
4. Build and test the exact coordinated package/update candidate before asking the user to test it on Lenovo. Actual Lenovo microphone/speaker quality, echo cancellation, interruptions and GPU appearance remain hardware gates.

No release package archive, ISO, channel, signing key, trust enrollment or Lenovo state was changed. Published staging sequence 4 / Hub 0.3.0 and the frozen unsigned Hub 0.3.1 / Voice 0.1.3 candidate remain unchanged. The private Mac provider testers were not restarted or reconfigured.

## Closeout

The final real control-socket snapshot showed disabled voice, microphone off, LiveKit mode, Ashley selected, and Cedar retained for Realtime. The canonical harness `stop_vm` completed and its PID file was removed; the disposable overlay is preserved. The owned installed-test and preview containers were stopped. No other running container or Mac provider tester was stopped. `git diff --check`, new documentation link checks and exact revision checks passed.
