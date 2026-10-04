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

## First live feedback

The person held a Gemini conversation at 15:26–15:31 and reported that the eyes and mouth still felt like the older version. Confirmed: an offscreen side-by-side of 5f422bd4 and 35204afb in listening and speaking with the same simulated envelope is nearly identical. Listening and speaking map to the idle mood, whose glances move the eyes about 2 px at 88 px, and the mouth was intentionally unchanged. The new moods sit on states a Gemini voice conversation rarely shows: connecting lasted 0.35–0.72 s per the audit log (shorter than the blend plus look-around), Gemini emits thinking only for typed turns (`livekit_gemini.py`), and error, completion and paused need those events. Step 2 (lighting) would not change this; the conversation states need their own moods (step 3).

## Conversation moods and Obsidian notes (0.1.5-29)

The person asked for complete implementation of the conversation moods and for spoken brainstorms to become structured, researched Obsidian notes written by an agent.

**Orb (`bd881a77`).** Listening keeps eyes about 10% larger that dart (±4 units), tilt (±7°) and widen and lift with the input level; speaking nods as the turn starts, sways (±6°), lifts and squints the eyes and bobs the body with the playback level, and opens the mouth rounder. A conversation started from ready or setup plays a 1.3 s wake (half-shut eyes open, look left and right, settle). The first render of step 3 showed the wake never playing because the previous state was only recorded on change; it is now recorded at creation, which would also have affected the installed orb's first conversation. An offscreen side-by-side of the old and new orb with the same simulated envelope, and a states × time sheet, were inspected: listening and speaking are now clearly distinct from ready.

**Notes (`8c7b8d34`).** Gemini's `write_note(request, research)` starts a background Codex seat (`note-1`/`note-2`) in the open Obsidian vault (`~/.config/obsidian/obsidian.json`). The daemon writes a private brief with the whole conversation (plus the previous one if it ended under 30 minutes ago) and fixed rules: read the vault, interpret intent and subtext, mark inferences, structure by content, frontmatter/summary/"What you're focused on"/next actions/open questions, link related notes, optional linked research note with sources, only new files inside the vault, finish with "Saved <path>". Obsidian is also an allowlisted app. Details are in `voice/docs/execution.md`.

Two defects were found while testing against real Codex 0.157.1 and fixed with regression tests:
- Codex's "Trust this folder?" dialog ignores `y` and `1`; Enter accepts it. Approve now sends Enter for that dialog. The first note in a vault holds its instruction until the person answers, then sends it after the dialog closes; a refusal ends the seat.
- A fresh agent shows that dialog a few seconds after its pane exists, so `tell` checked too early and then waited for an input box that never appeared (`AGENT_NOT_READY`). `tell` now waits for the input box or a question first.

Evidence:
- Tests: 426 Python tests OK (two expected skips), orb contract and frame tests, UI/controller and launcher checks, `git diff --check`.
- Real Codex (source, throwaway vault with two seed notes, a five-turn brainstorm with "Obsedian" misheard, research yes): trust prompt detected and approved, instruction delivered, finished in 2 min 36 s. It wrote `Voice Notes/2026-10-04 Maslow priorities and dog walker idea.md` (day plan, focus, inferred subtext, links to existing notes) and `Research/Dog walker business tool - Research.md` (APPA market context, competitor pricing table with links, positioning, launch plan, three experiments, risks); existing notes were unchanged. The two probe trust entries added to `~/.codex/config.toml` were removed; the file matches its pre-session content.
- Real Gemini 3.8 Live text session from source (temporary state, stubbed seat): two brainstorm turns got short reflective replies and no action; "put all of this into my Obsidian, plan tomorrow and research…" produced one `write_note` with research `yes` and the request in the person's words; the brief contained all three messages.
- Package: recipe `1fb190a` (`0.1.5-29`), archive SHA-256 `411b07c14bce042ab8f34bcdf34f1465c863ab15892c355805bf088779556df1`; packaged UI and Python files match `8c7b8d34`. Logs: `voice-mvp-build/voice-orb-notes-29/`.

- Installed: `pkexec pacman -U` installed `0.1.5-29`; `pacman -Qkk` reports 9126 files, 0 altered. The service was restarted to load the new Python and the plugin rescanned behind the unlocked-desktop guard; the manifest points at `0.1.5-29/Panel.qml` and the ready orb was observed with open eyes. Mistake: idleness was checked before the install but not again before the restart, and the restart ended a conversation the person had started 36 s earlier (16:25:35–16:26:12; no completed exchange in the audit log). Check Voice state immediately before any service restart.

Not verified: spoken (audio) note requests, the first trust answer by voice in the person's real vault, the spoken result announcement for a note, and Claude Code or Hermes as note writers (Codex only).

## Next action

The person tests a spoken brainstorm ending in "put this in Obsidian" (first use asks to trust the vault) and the new orb moods in a real conversation.
