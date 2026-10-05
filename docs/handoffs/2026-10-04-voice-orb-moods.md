# Voice orb moods, Obsidian notes and conversation flow

Date: 2026-10-04. Goal: make the orb's face expressive by porting the eye choreography of [Moodstone](https://github.com/karacca/moodstone) (MIT, reviewed at `5d3d2568`, release 1.0.1) into the native QML orb, keeping Maslow's audio-reactive body, mouth, theme colors and fallback renderer. This is step 1 of the orb plan agreed in conversation; lighting (step 2), Voice-specific moods such as listening lean-in and needs-approval (step 3) and task moods on the face (step 4) remain.


**Iteration status (October 5): closed as good enough, not complete.** The person asked to stop here and move to other areas. Runtime branch `codex/voice-orb-moods` is merged into `main` and pushed to GitHub; the recipe branch `voice-orb-moods` in `maslow-os-pkgs` (`0.1.5-33`) is pushed as a backup and not merged into `maslow`. Local `maslow-voice 0.1.5-33` is installed on the Lenovo. Nothing is published.

## Iteration summary

- **Orb:** Moodstone-derived eye moods (MIT) plus Maslow's own listening, speaking and wake moods that follow the live voice level; frame-clock animation; listening/thinking/speaking shown only after 250 ms so flicks within a turn do not jitter the orb or status text.
- **Obsidian notes:** `write_note` sends the whole conversation, plus recent web task answers, to a background Codex in the open vault, which writes structured notes and, when useful, a linked research note with sources. Codex's first-use folder trust question is answered by voice.
- **Conversation flow:** actions answer Gemini within 0.8 s and finish in the background; updates carry the agent's closing message, not its terminal screen; a dropped Gemini session reconnects quietly with the conversation; follow-up tool calls cannot loop or produce false errors.
- **Open issue:** the person reported speech stopping mid-sentence around multi-step website requests, even with the microphone muted. It could not be reproduced. See "Known issue: speech cut off around actions" below for the playbook.

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

## First real test and 0.1.5-30

The person ran a spoken session (16:37–16:47): two website opens, a web task (finished 16:42, spoken), then a note. They reported it went fine except a jitter of the text and orb in thinking mode.

Log findings:
- The first note at 16:43:10 failed with `AGENT_NOT_READY`: the background Codex took longer than the 8 s start limit while a web task was busy. Background seats now get the 20 s input wait.
- After that error Gemini produced about 30 short generations in 18 s (16:43:11–16:43:29). Follow-up generations have no spoken turn, so their tool calls were refused with "please repeat the request", which the model obeyed in a loop; each refusal also emitted a task error event. The refusal is now `NO_SPOKEN_REQUEST`, tells the model to stop and explain, and emits no event.
- The second attempt worked: trust prompt 16:44:00, spoken approval 16:44:15, note saved 16:47:13 (`Voice Notes/2026-10-04 Blind Dog Enrichment App.md` with a 151-line linked research note, 20 links). Codex said the conversation held no earlier search results: the web task's answer had only been spoken. Briefs now include final answers of web tasks finished in the last hour (job results keep 2000 characters).

Jitter: LiveKit agent states flick between listening, thinking and speaking within a turn; each flick changed the orb mood (eyes starting to merge), shrank the body 6% in one frame and swapped the status text. The Panel now shows those three states only after 250 ms (`settledState`), the orb animates on `FrameAnimation` by real frame time instead of a 25 fps timer, and body scale eases. The retry loop above was a second source of flicker.

Commits `3deda09e` (smoothness, loop, startup wait) and `c6b24c7d` (web results in notes); recipe `4d2d50c` (`0.1.5-30`), archive SHA-256 `fa2d12761ffe90d66df7a9eb9d6269baff0df90b0c528c910a3eff35c4724230`. 428 Python tests OK (two expected skips), orb/UI/controller/launcher checks pass, GPU preview rendered with the frame clock and no QML warnings. Installed with 0 altered of 9126 files; Voice was confirmed idle immediately before the restart; plugin rescanned behind the unlocked guard; the ready orb was observed and the shell log has no Voice errors. Smoothness on the physical display during a real conversation is for the person to confirm.

## Conversation flow and dropped sessions (0.1.5-31)

The person reported that opening the browser or Codex stopped the conversation mid-sentence and resumed when the page loaded, and that "Connection lost · click to retry" appeared, reproducibly when asking for an Obsidian note.

Findings:
- Gemini 3.8 Live waits silently for each tool result. Opening an app waits for its window; agent, web and note actions wait for Codex to start. Gemini's `NON_BLOCKING` tool behaviour, supported by the pinned plugin, did not help in a real text session (the reply came later: 23.1 s against 13.4 s).
- 11 Gemini 1011 "internal error" drops in three days, between 7 s and 9 minutes into sessions. The four that followed an action within 5 s all followed Codex screen text or a note job reaching the conversation (note start, `agent_status` on a note or Codex seat, a note's finished update); web task updates (0 of 4) and website opens (0 of 9) never did. A real text session with the same note screen did not reproduce it. Cause unconfirmed.

Changes in `60a0004f`: desktop, agent and note actions answer within 0.8 s and finish in the background (only a failure or a waiting question is said later; retries reuse the receipt); updates carry the agent's closing message instead of the screen; a running Gemini conversation that drops with `GEMINI_CONNECTION_FAILED` reconnects at most twice per 180 s, keeping session, transcript, mode and extended setting, with a briefing to continue without greeting.

Evidence: 432 Python tests OK (two expected skips); real Gemini text session with a six-second action replied at 6.5 s, before the action finished at 7.1 s; a real reconnect took 0.3 s and the model still recalled details from before the drop. Recipe `7bd65c4` (`0.1.5-31`), archive SHA-256 `2037441c991f87f1c3b24ebbc0a93203fcd91e4c057d526ddbb0464fc8ecc90b`; installed with 0 altered of 9126 files; Voice idle immediately before restart; plugin rescanned; ready orb observed. Not verified: real server drops with audio and the person's perception of the flow.

## Speech cut off around actions (0.1.5-32)

The person reported that speech still stops mid-sentence around multi-step website requests, with the microphone physically muted. Their 19:47–19:56 sessions had no Gemini drops, and every action answered within 1 s. Six recorded real Gemini sessions through a fake sound card did not reproduce it (details in `voice/docs/execution.md`); synthetic espeak speech was misheard, so spoken turns, where Gemini may talk before acting, remain untested. `f7593996` tells Gemini to act first or finish its sentence and to batch actions, and adds a word-free speech timeline to the journal (`Voice speech state`, `Voice speech interrupted`, `Voice speech gap`). 434 Python tests OK (two expected skips). Recipe `43678b8` (`0.1.5-32`), archive SHA-256 `d0658245677fbce1bdf57740ab7a45ea609e74efd201b3d971269be32f427180`; installed with 0 altered of 9126 files; Voice idle immediately before restart; plugin rescanned; conversation ready.

## Final fix and release (0.1.5-33)

While the speech timeline harness (`voice/dev/speech_trace.py`, now in the repository) was being checked, it caught a new defect: a slow action's `started` answer made Gemini call the tool again from its follow-up; that call was refused and Gemini told the person the action had failed although the browser had opened. `7f3769b8` tells Gemini to treat a started action as done and makes the refusal say an earlier action is already under way. Three harness runs then gave a correct, complete answer each. 433 Python tests OK (two expected skips); orb, UI, controller and launcher checks pass. Recipe `6c3e0b8` (`0.1.5-33`), archive SHA-256 `172e959213103fd0d726caecae22216289dda81d5ef91678be2904253a6ebabc`. Installed with 0 altered of 9126 files; Voice was confirmed idle in the same command that restarted it; the plugin was rescanned behind the unlocked guard and points at `0.1.5-33/Panel.qml`; conversation readiness is true.

## Known issue: speech cut off around actions

Reported on October 4 and not reproduced. The person heard Maslow stop mid-sentence while working on multi-step website requests and continue later, also with the microphone physically muted, so it is not barge-in. Ruled out with recorded real Gemini sessions: typed multi-action requests (Gemini acts first, then speaks one answer), job updates (they wait for the end of speech), full CPU load (no playback gap), launch scripts (no audio side effects) and discarded generations (never logged in production). The leading hypothesis is Gemini calling a tool mid-sentence in spoken turns, which typed tests cannot show; `f7593996` instructs it to act first or finish the sentence.

If it is reported again:
1. Ask for the approximate time, then read the journal around it: `journalctl --user -u maslow-voice --since <time-2min> --until <time+2min> | grep -E "Voice (speech|action|notice|reconnecting)"`.
2. Interpret the timeline:
   - `Voice speech gap <s>` while speaking, close to a `Voice action … started`: Gemini paused its own reply for a tool call. Consider buffering the reply across tool calls, or answering instantly for opens.
   - `Voice speech interrupted`: something counted as the person speaking; check echo and the input path.
   - `Voice reconnecting`: a Gemini server drop (1011), recovered automatically; check how often it happens.
   - None of these: the cut is outside the daemon; record the screen with sound (`omarchy screenrecord`) and compare.
3. Try to reproduce with `voice/dev/speech_trace.py` and the same request. Spoken turns need a real person or a better synthetic voice than espeak.

## Remaining gates

- The person has not tested `0.1.5-31` to `0.1.5-33` (smooth flow, reconnect, false-error fix) by voice.
- Speech cut-off around actions (above).
- Gemini 1011 drops: the cause is unconfirmed; reconnect hides them, at most twice per three minutes.
- Orb lighting (step 2) and task moods on the face (step 4) were not done; the orb gallery and harness are ready for them.
- Claude Code and Hermes are not used as note writers (Codex only).
- Carried over from the agent-terminal iteration: orb/Work view for web jobs, tidying finished browsers, Claude live keys, structured agent status instead of screen reading, memory and the wake-word decision.
- Release work (package merge to `maslow`, signing, channel promotion, ISO) remains separately authorized.

## Next action

When Voice work resumes: have the person try one spoken session with a multi-step website request and a note on `0.1.5-33`, and if speech is cut, follow the playbook above.
