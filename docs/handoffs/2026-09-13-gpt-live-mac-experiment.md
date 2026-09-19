# GPT-Live Mac experiment and simpler task handoff

Date: 2026-09-13. Active checkout: `/Users/r.david/.codex/worktrees/maslow-voice/livekit-runtime`, branch `codex/livekit-setup`. This is development evidence, not an update candidate or native Linux acceptance.

## Product direction

The user requested a local test of GPT-Live with continuous conversation while a separate local agent handles work. They subsequently asked whether opening existing agents with keyboard shortcuts and giving them the task would be simpler. The recommended first product slice is a small handoff service: the user names or selects Hermes, Codex, or Claude; Maslow prepares a task and uses the destination's supported prompt interface. Existing Omarchy launch commands and shortcuts remain the familiar app entry points. UI paste is a fallback when a supported interface is unavailable, with weaker submission/completion guarantees.

Hermes need not be a mandatory planner between Voice and a user-selected coding agent. Automatic agent selection, formal A2A interoperability, comprehensive task recovery, and general desktop/browser execution are separate capabilities. Do not convert this isolated experiment into a second production orchestrator or replace the existing execution adapters without a scoped integration decision.

## Verified audio evidence

- The actual `gpt-live-1` endpoint accepted the user's RAM-only OpenAI key. The synthetic Marin probe recognized the fixed test sentence, received non-silent PCM, and finalized normally with zero reported API errors. First recorded run: 246 input packets, 44 output packets, 4,400 ms returned PCM including silence, final usage 4 seconds.
- The user started a real native Mac conversation and reported **“Smooth and responsive”** when asked about speech quality and interruptions. Safe metrics recorded 7,786 input packets, 1,506 output packets, one delegation notice and one accepted context update, zero reported API errors, and confirmed normal closure with 158 seconds final usage. The task runner was unavailable during that conversation; it did not establish task execution.
- Quartz speaker-only preview also passed: 617 input silence packets, 118 output packets, one context append/acknowledgment, no user transcript deltas, no API errors, normal closure with 12 seconds final usage. This establishes that this additional voice returned playable native audio, not that all listed voices have been auditioned.
- No raw user transcript, microphone recording, account key, or raw provider debug output is included in retained evidence. Safe files are under `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/gpt-live/live/`.

## Task experiment and defects found

The prototype uses the existing TaskManager for lifecycle and a separate local Hermes process for planning and bounded artifact generation. It is a local process adapter, not a proof of the Hermes HTTP Runs API or a formal A2A exchange. The executor has no model tools; a host validator writes only the selected scratch artifact after checking cancellation, previous contents, and path ownership.

The first ambient Hermes attempt did not honor the scratch working directory. Two diagnostic artifacts written in the home directory were moved to Trash by the worker. Subsequent testing uses a separate temporary HOME/HERMES_HOME and a Mac write sandbox. The original Hermes user configuration is not modified. Codex's discovered CLI entry point also reported a missing vendored binary; installation repair and Claude execution are outside this experiment.

Local inspection found that an empty `--toolsets` argument did not reliably disable tools and that Hermes recovered a kanban toolset. The final isolated profile was checked against the installed resolver and produced zero tools. It excludes ambient dotenv files and writes no API key to disk. The current key is passed through the child process environment. Session database/debug dump writes are denied to keep delegated conversation context out of Hermes logs.

The actual spoken scenario reached a GPT-Live delegation and context acknowledgments, but its first planner attempt failed before creating a task. Safe diagnostics then identified a provider-name mismatch: this installed Hermes expects `openai-api`, while `openai` is rejected before any model request. Correcting that allowed the child to exit successfully; the next actual response failed the constrained JSON contract. Parsing now accepts plain JSON or one enclosing JSON Markdown fence, while rejecting surrounding prose and multiple objects. Safe synthetic-only diagnostics established a further HTTP 400: the model did not support the reasoning parameter Hermes sends from its oneshot path. Installed-source inspection showed that this path ignores the interactive reasoning option, so the private runner now uses compatible `gpt-5-mini`. The constrained brief prompt was also made explicit about list field types.

After those corrections, the actual typed request completed through the separate local Hermes process. The host verified a newly generated 541-byte `result.html` containing Water, Snacks, Rain jacket, and First aid; SHA-256 `1fdb3cf3821d423ed2b2db7ca4a48405ea5dc528be0c8971b116776165ac5923`. Evidence: `gpt-live/live/typed-artifact.json`. The subsequent actual spoken scenario also passed: one GPT-Live delegation produced a new 1,712-byte artifact, spoken response deltas advanced while the task ran, two context updates were acknowledged, and the session finalized normally with 61 seconds usage and zero API errors. Evidence: `gpt-live/live/voice-handoff-passed.json` and the retained `voice-result.html`. This is a synthetic audio scenario; the separate native feedback above covers actual microphone and perceived voice quality.

A real running task was then cancelled. Its state became cancelled and the previously verified artifact hash was unchanged. Evidence: `gpt-live/live/cancel-running-task.json`. Cancellation race, stale output, concurrent file change, duplicate delegation, and same-task attempt behavior also have focused regression coverage.

A subsequent correction reused the same task at attempt 2, remained running immediately after Stop audio, and completed with the requested Map item and no cancelled-test heading. The 532-byte corrected artifact is retained with `correction-after-voice-stop.json`. Its first startup sample read stale cached audition metrics and was false; the final session close confirmed startup, closure and usage. This instrumentation defect is recorded rather than erased. The tester now publishes the active provider metrics for every mode, with a regression test. This is a speaker-only session lifecycle check; it does not replace the separate native microphone feedback.

## Implementation and validation boundary

The new `OpenAILiveProvider` is separate from the production provider factory. It uses continuous input, independent listening/speaking state, raw transcript deltas, opaque delegation notices, host context appends, cumulative usage, and bounded final session closure. It does not fabricate Realtime items, final voice turns, or executable tool calls.

The private tester is on `http://127.0.0.1:57519/`. It uses the same loopback Host/Origin/nonce boundary as the existing testers. The saved key stays in RAM. Provider/host fixes can reload between sessions. Task controls and a synthetic voice-handoff scenario are development-only. Stop audio does not cancel accepted tasks; Clear connection and stop test tasks closes the owned scratch runner. The task database is temporary, so tester-restart recovery is not proven.

The complete Voice suite ran 177 tests: 175 passed and two Linux namespace tests were skipped on macOS. The private tester suite passed 22 tests; JavaScript syntax and whitespace checks passed. The final backend prompt adjustment was followed by another 20 passing focused backend tests. A running browser inspection confirmed the controls render at the narrow in-app viewport. Keep artifact proof, synthetic cloud proof, native microphone feedback, lifecycle regression tests, and later Lenovo acceptance separate.

## Source checkpoint

- `79b558a7`: experimental GPT-Live adapter and focused protocol tests.
- `bdd0b7f0`: private Mac tester, isolated Hermes scratch adapter, lifecycle tests and usage guide.
- These commits are local to `codex/livekit-setup`; no source push or production provider switch was performed. The final tester was left idle with microphone off, no error, its key retained in RAM, and two completed scratch tasks.

## Preserved release and test state

LiveKit remains on port 57517 and OpenAI Realtime on port 57518 with their independent RAM-only connections. Do not restart those testers casually or request account keys in chat. The user-confirmed LiveKit voice choices and the Realtime provider are preserved.

No Hub/package/ISO change, signing, release publication, or Lenovo update was performed. Public staging remains sequence 4 / Hub 0.3.0. The unsigned Hub 0.3.1 / Voice 0.1.3 candidate remains frozen. The native flat orb, installed GPT-Live integration, actual coding-tool/app handoff, and Lenovo hardware acceptance remain later gates. Use Docker/Weston/Quickshell for native UI iteration and the existing headless QEMU/TCG harness for installed-system proof; no UTM.
