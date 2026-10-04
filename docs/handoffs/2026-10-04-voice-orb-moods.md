# Voice orb eye moods (Moodstone port, step 1)

Date: 2026-10-04. Goal: make the orb's face expressive by porting the eye choreography of [Moodstone](https://github.com/karacca/moodstone) (MIT, reviewed at `5d3d2568`, release 1.0.1) into the native QML orb, keeping Maslow's audio-reactive body, mouth, theme colors and fallback renderer. This is step 1 of the orb plan agreed in conversation; lighting (step 2), Voice-specific moods such as listening lean-in and needs-approval (step 3) and task moods on the face (step 4) remain.

## What changed

- `voice/ui/OrbFrame.js` (new, `.pragma library`): a port of Moodstone's `frame.ts`/`math.ts` with the MIT notice. Each mood is a pure function of time: idle, observing, thinking, working, done, failed, inactive, plus a static Maslow `resting` pose. Rest geometry and the largest vertical travels are adapted to Maslow's taller pupil eyes and mouth; timing, easing, blinks and choreography are Moodstone's. Sleep marks stay inside the body so they never draw on the desktop.
- `voice/ui/VoiceOrb.qml`: eyes, pupils, mouth, dizzy swirls and sleep marks are driven by the frame. State mapping: ready/listening/speaking → idle (glances, natural blinks); connecting → observing (look-around with head turn); thinking → merged bobbing dot; working → line reading; paused/muted → resting half-shut; disabled → asleep with "z"s; error → fall, bounce and dizzy once, then hold the fallen pose (animation stops); completion → one happy squint, jump and wiggle (2.6 s, replaces the 0.65 s bounce); interruption → one quick blink. Mood changes ease over 300 ms on their own clock so static states finish the transition. Reduced motion shows each mood's key pose. The old 4.2 s fixed blink timer is gone. Body deformation, input/playback separation and theme ink are unchanged; the shader is byte-identical.
- `voice/tests/orb-frame-test.mjs` (new): containment of eyes/swirls/marks inside the body for every mood over 1.5 loops, seamless loops, held one-shot ends, done ending at rest, fallen error without swirls, key expressions, blend endpoints and the interruption blink. Added to `test/shell.d/voice-test.sh`.
- `voice/tests/orb-contract-test.mjs`: `moving` now includes the error fall; state → mood mapping asserted.
- `voice/tests/orb-preview.qml`: adds `working` and a `completed` reaction column; `GALLERY_FRAMES=n` saves numbered captures 400 ms apart.

## Commits and artifacts

- `maslow-os` branch `codex/voice-orb-moods` from `main` at `5f422bd4`: `35204afb` (implementation and tests). A documentation commit records this handoff.
- `maslow-os-pkgs` branch `voice-orb-moods` from `voice-agent-terminal` at `6fd9364`: `8d1b60c` advances the recipe to `0.1.5-28`.
- Build: `git archive` of `35204afb` and recipe `8d1b60c`, built in `maslow-voice-builder:preferences` with `OMARCHY_SRC` and `makepkg -d`; `check()` passed. Archive SHA-256 `a75a38d8bffb9581a476b9dc6d6e170b015d91814030ad44b285dbd34052de44`. Packaged `OrbFrame.js`, `VoiceOrb.qml` and `Panel.qml` match the frozen source; `VoiceOrb.frag.qsb` is identical to 0.1.5-27. Inputs, build and install logs: `voice-mvp-build/voice-orb-moods-28/`.
- Nothing pushed or published.

## Evidence

- Tests: `bash test/shell.d/voice-test.sh` ran 414 Python tests OK (two expected skips) plus the UI, orb contract and new orb frame checks; `node voice/tests/ui-controller-test.mjs` and `bash test/shell.d/voice-launch-test.sh` passed. `git diff --check` clean.
- Canvas/software renders (builder image, `QT_QPA_PLATFORM=offscreen`, `QT_QUICK_BACKEND=software`, `MASLOW_VOICE_GPU_SHADER=0`; no Weston on this host): galleries in the active Maslow theme and Catppuccin Latte, a reduced-motion gallery, and a 14-frame states × time sheet at 88 px, all inspected. Observed: blinks and glances, look-around, merged dot bobbing, line reading, fall → dizzy → held flat eyes, completion squint/jump/wiggle returning to rest, static resting and sleeping faces. No QML warnings after fixing an initial `face` binding loop (the face now reads `shownMood`, set only by the change handler).
- GPU path: the same preview run on the Lenovo's Hyprland display (2× scale, six frames) rendered through the shader with crisp faces.
- Installed: `pkexec pacman -U` installed `0.1.5-28`; `pacman -Qkk` reports 9125 files, 0 altered. The plugin was rescanned with the launcher's guard (desktop unlocked, lock service confirmed back afterwards); the manifest points at `0.1.5-28/Panel.qml`. Eight live captures of the installed orb (ready state) show open eyes glancing; one earlier capture caught a blink. The service was not restarted (Python files unchanged) and no conversation or account request was made.

## Not verified

- Live states other than ready on the installed orb: connecting, listening, thinking, speaking, paused, error, completion and interruption on a real conversation. These are covered by fixtures only.
- Display resize/scale change, drag, and long-run CPU use (the face recomputes at the existing 25 fps tick).

## Next action

The person tries the installed orb in a real conversation (connect, talk, pause, a delegated task finishing) and reports how each state feels; then step 2 (orbiting light and grain in the shader and Canvas fallback).
