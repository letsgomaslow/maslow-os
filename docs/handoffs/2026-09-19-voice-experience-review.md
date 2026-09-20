# Voice experience review and discussion proposal

Historical record with dated follow-ups. For the current product scope and acceptance limits, read [the product and lessons reference](../maslow-voice-product.md) and [development index](../maslow-development.md). Earlier statements about pending installation or missing capabilities apply to their recorded checkpoint, not necessarily the final installed candidate.

Date: 2026-09-19. Status: research and architecture discussion, not an approved implementation specification. Reviewed runtime `4b3795b7` on clean `main`. No runtime, installed configuration, provider accounts, packages, or delivery state changed.

## Product intent

Maslow Voice should support natural conversation, precise desktop control, and delegated background work through one primary Orb. The person describes outcomes; Maslow organizes context, resolves workspaces, selects capabilities, and returns verified results. Thinking aloud must remain possible without every idea becoming a task. This is an executive-assistant product direction, not a relationship simulation or a medical intervention.

## Confirmed source boundaries

- `voice/maslow_voice/execution.py` defines default application names for browser, files, Hub, and terminal. Codex, Claude, and Hermes are not default desktop-launch targets; agent execution is a separate integration.
- `voice/maslow_voice/tasks.py` and `voice/maslow_voice/daemon.py` explicitly reject delegated work without an existing project folder. Workspace inference and automatic project provisioning are product gaps, not something a conversational prompt alone can repair.
- `voice/docs/execution.md` describes the validated task boundary, selected-agent routing, task identities, approval handling, and separate conversation readiness. Preserve those foundations while adding a bounded desktop-action path independent of coding tasks.
- Direct Codex/Claude jobs are currently in-process and non-resumable after daemon loss; direct mid-turn steering is unavailable. Durable background execution requires additional work.
- `voice/ui/VoiceOrb.qml` receives microphone amplitude; speaking uses a state-driven cadence. Thinking and working share a state mode. Foreground conversation and background task status need independent representation.

These findings explain likely friction but do not reproduce the person's exact refusal. No private transcript or live provider session was inspected. Existing September 19 package and hardware acceptance limits remain unchanged.

## Proposed architecture

1. Conversation session: low-latency speech, interruption, incremental transcript, short responses, and continuity while work runs.
2. Context resolver: explicit named project first, then an established conversation project, then trustworthy app/workspace context. Use a managed scratch workspace for a new reversible task; ask only when ambiguity materially affects the outcome. OS actions and captured ideas require no code project.
3. Local capability broker: typed operations for launch/focus, terminal-agent launch, website/webapp open, workspace changes, installation through supported helpers, and task submission. Validate arguments and permissions outside the model. Return observed outcomes, not success inferred from an attempted launch.
4. Durable work supervisor: persisted jobs and attempts, worker ownership independent of Voice audio sessions, progress, scoped cancellation, approval checkpoints, restart reconciliation, and artifact verification. Preserve each adapter's actual capabilities; never pretend an interrupted non-resumable run was resumed.
5. User-controlled memory: separate original words, ideas, decisions, commitments, projects, and verified facts. Retain provenance and uncertainty; allow correction, inspection, forgetting, and expiry. Durable jobs and selected memory should outlive ephemeral speech sessions.
6. Attention policy: prepare low-risk research under standing scope and budgets, deliver results at conversational pauses, and interrupt only for time-sensitive decisions. External publication, purchases, credential entry, and privileged operations retain their applicable boundaries.

Prefer existing Omarchy helpers, desktop IDs, Hyprland state/events, and application APIs. Use browser/desktop automation where structured control is absent. Hyprland window control does not itself provide semantic control inside every application. Untrusted documents and web pages cannot authorize actions or change standing policy.

Background tool submission should return a job receipt promptly and deliver completion later. Provider-native asynchronous function calling varies by model; the local supervisor must own durability independently.

## Proposed Orb language

Keep one stable, user-positioned Orb and preserve one-action activation. Explore three directions: a soft fluid body, a precise luminous ring, and a restrained glass body with a readable outer ring. Prefer the third as the first prototype because it preserves the current visual investment while making status clearer.

| State | Proposed signal |
| --- | --- |
| Idle, microphone off | Still, subdued body |
| Connecting | Finite directional motion with timeout/error transition |
| Listening | Stable capture indicator plus input-reactive surface |
| Interpreting a turn | Gentle inward motion distinct from speaking |
| Speaking | Outward movement driven by actual playback amplitude |
| Background work | Small independent outer mark; conversation stays available |
| Needs a decision | Persistent distinctive mark and optional short label |
| Finished | One brief completion transition; no perpetual celebratory motion |
| Muted or failed | Distinct static shape/icon and accessible text |

Color alone is insufficient. Reduced motion must preserve all status distinctions. Optional captions and a compact task/result surface are necessary for exact filenames, decisions, and review; they need not become a permanent dashboard. Microphone capture must remain apparent during assistant playback and background work.

## First vertical slice and acceptance proposal

Use one conversation: “Open Codex” → “Make a small prototype for this idea” → discuss another topic while it works → “How is it going?” → inspect the artifact → stop or correct the task. Require no folder selection for opening an app or starting a new scratch task.

Verify actual app/window readiness, correct task/workspace binding, continued conversation, interruption without accidental job cancellation, explicit job cancellation, missing-agent setup, required sign-in handoff, service-restart behavior, and resulting artifact content. Test Orb state recognition at its actual desktop sizes, with reduced motion and physical audio. Latency and comprehension targets should be defined before measurement; none are claimed here.

## Authentication constraint

One onboarding experience is a reasonable target; universal access from any one vendor subscription is not established. Current Gemini conversation requires its Google credential, while the current Claude adapter explicitly uses a separate API-key path. Codex supports subscription or API-key authentication. Product options include managed Maslow billing, supported user-provider connections, and local modes, with capabilities and limits shown accurately. Never reuse subscription credentials through unsupported mechanisms or silently switch billing routes.

## Research references

- [ElevenLabs Orb](https://ui.elevenlabs.io/docs/components/orb): example of explicit listening/thinking/talking state and audio-driven visualization; visual reference, not a proposed dependency.
- [Google conversation confirmations](https://developers.google.com/assistant/conversation-design/confirmations): implicit confirmations and one-step corrections, with explicit checks for costly mistakes.
- [LiveKit turn-taking tuning](https://docs.livekit.io/agents/logic/turns/tuning/): endpointing and interruption are distinct tuning concerns; this research does not resume the deferred LiveKit provider experiment.
- [Gemini Live tools](https://ai.google.dev/gemini-api/docs/live-api/tools): function calls and model-dependent asynchronous behavior.
- [Hyprland IPC](https://wiki.hypr.land/IPC/): compositor commands and event observation for desktop state.
- [Codex authentication](https://developers.openai.com/codex/auth/): supported subscription and API-key paths.

## Closeout

Read-only source review and primary-source research completed. No implementation, live conversation, graphical inspection, provider comparison, build, or hardware acceptance was performed. Documentation checks cover relative links, recorded revision, and whitespace only. No commit or publication is part of this discussion checkpoint. Next action: agree the first end-to-end conversation scenarios and use them to specify the desktop-action/workspace boundary and Orb state prototype.
