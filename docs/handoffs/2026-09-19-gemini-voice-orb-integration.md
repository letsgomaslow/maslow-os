# Gemini Voice and movable Orb integration

Date: 2026-09-19. Scope: record the functional Lenovo source candidate, the architecture and troubleshooting conclusions reached since the September 16 failure report, the installed local package evidence, the completed source integration, and the remaining Voice UX and product acceptance work. This handoff supersedes the September 16 handoff as the current Voice development checkpoint. It does not replace the immutable evidence for older published GPT-Live or Hub artifacts.

## Current result

Maslow Voice is now a functional source and local-package candidate on the Lenovo development laptop. The current default conversation mode is Gemini Live through Google AI Studio. GPT-Live, OpenAI Realtime, LiveKit Expressive, model-server, and offline modes remain selectable. The conversation layer can produce a transcript-backed task, and the separate execution layer can route that task to Codex, Hermes, or Claude according to an explicit spoken preference or automatic routing policy.

The installed local candidate is `maslow-voice 0.1.5-7`, built from runtime source `da6f6f140d80fe079b19d55ea39bd5c6284565d5` and package recipe `46a0971`. Its local package SHA-256 is `ee44e33181d5183a313eb0a06281b5cdcaa8b3efbd4c6fb20326b94882d50b74`. The service was active after installation and Voice was deliberately left ended with the person's prior bottom-right pin preference restored. These identities describe local development evidence; the package has not been signed, published, promoted, or included in a new ISO.

The current Orb is a working visual direction rather than a final brand design. It uses a blue glass body with three curved internal sheets, white/ice highlights, and restrained Maslow teal and purple accents. The GPU shader and software Canvas fallback implement the same structure but are not expected to be pixel-identical. The result has more depth and state motion than the original flat Orb. The current internal lines, exact blue balance, motion language, and personality still need a deliberate Maslow brand review.

## Implemented behavior

### Conversation and task routing

- A new settings file selects Maslow Voice (`gemini_live`), Gemini model `gemini-3.8-live`, voice `Puck`, automatic peer routing, and `lab_auto`. Existing valid provider choices are preserved during upgrades.
- Gemini connects directly to Google AI Studio through the LiveKit Agents Google realtime plugin and the native local audio transport. It does not join a LiveKit room and does not consume LiveKit project credentials.
- Gemini supplies native audio replies, input/output transcription, and turn detection. Each tool call is bound to the final user transcript from its own generation. A call without a final transcript fails closed.
- The conversation model does not execute commands. It can submit one validated task intent. `TaskManager` persists the original words, selected project, task identity, selected agent, routing reason, status, approvals, and result.
- Explicit requests for Codex, Hermes, or Claude select that peer. Automatic routing considers the configured default, then Codex, Hermes, and Claude without duplicates. An unavailable explicitly named agent fails visibly instead of silently rerouting.
- `lab_auto` starts a validated explicit work request. `review` records it as a proposal until the person starts it. These policies do not bypass the selected agent's own approval and permission behavior.
- Typed input can promote an existing Gemini conversation to microphone capture without creating a second session. Task setup errors remain visible without disconnecting an otherwise usable conversation.
- Conversation inactivity is based on completed conversational turns rather than ambient microphone energy. Desktop lock ends capture and every session has a hard 30-minute limit.
- The private bounded audit log records provider/model, duration, reported usage, agent selection, and safe error codes. It excludes audio, transcripts, credentials, and raw SDK diagnostics.

### One-action Voice UI

- The Orb is the primary action. One short click starts listening when conversation readiness is complete. When readiness is incomplete, the same click opens Advanced Voice settings with the failed checks instead of pretending to start.
- During a conversation, the Orb opens compact Mute or Resume, End, Captions, Tasks, and Settings controls. Press and hold opens Advanced Voice settings from idle.
- The Orb uses 56 pixels in the ready idle state and 88 pixels for conversation. Automatic placement is bottom right while idle, bottom center during conversation, and bottom left when work needs attention.
- The Orb can be dragged anywhere inside 16-pixel display margins. Its normalized position survives Voice service restarts and display-size changes. Dragging disables the bottom-right pin. Enabling **Keep orb at bottom right** atomically clears the manual position. **Reset orb position** returns to automatic state-driven placement.
- Reduced motion freezes the shader and Canvas motion. Keyboard activation and accessible state descriptions remain available.

### Orb material and palette

- `VoiceOrb.frag` provides the normal GPU path; the packaged `.qsb` includes the target OpenGL variants. A Canvas glass treatment and a deep-blue gradient base preserve visibility under software rendering or shader failure.
- The current Voice-specific tokens are deep blue `#154BA8`, blue `#2875E5`, light blue `#93C9FF`, cloud white `#EFF8FF`, teal `#73C1AE`, and purple `#654C8F`. Teal and purple are secondary accents inside a blue/white material.
- State changes alter cadence, deformation, rim treatment, and mute/error/disabled rendering. Microphone level drives listening response; speaking currently uses a state-driven cadence because playback amplitude is not published.
- The visual reference influenced the desired depth and fluid material, but the implementation is original code and uses Maslow-owned tokens. The remaining design work is to make the Orb recognizably Maslow rather than merely a polished blue sphere.

## Troubleshooting conclusions and root causes

| Symptom or question | Finding | Correction or consequence |
| --- | --- | --- |
| Clicking the grey Orb opened the older full Voice UI | A successful package install does not prove Quickshell loaded the new QML. Version-specific plugin paths and a deferred refresh marker are required because kept-loaded QML can remain cached. | Every visual package revision receives a new plugin path. Verify visible UI and shell/QML logs after installation, not only `pacman` success. |
| “LiveKit implementation” and Gemini appeared to require the same cloud setup | The Gemini implementation uses the LiveKit Agents runtime and Google plugin in process, but no LiveKit room or LiveKit project credentials. LiveKit Expressive is a separate optional cloud inference path. | The settings and documentation now distinguish the Google conversation account from optional LiveKit Expressive credentials and from task-agent authentication. |
| Voice could hear and transcribe nearby speakerphone audio, but it was unclear whether anything reached Hermes | Audio capture/transcription, conversation response, task extraction, routing, and agent artifact completion are separate gates. Hearing speech proves only the first part. | Readiness and UI state are split into conversation and tasks. Acceptance must inspect the recorded task, selected agent/run identity, and resulting artifact. |
| The user wanted unrestricted behavior while learning the risks | `lab_auto` removes the extra proposal/start step for explicit work, but it does not erase Codex, Hermes, or Claude permissions and approvals. | Observe behavior through the existing execution boundary. A future stronger security layer must be enforced outside conversational prompting. |
| GPT-Live cost versus Gemini/LiveKit cost and smoothness was unclear | The implementation now makes Gemini the new-install default while retaining GPT-Live and LiveKit Expressive choices. No controlled cost, latency, interruption, or conversation-quality comparison has been completed on this Lenovo. | Do not claim lower cost or equivalent smoothness until measured account usage and physical conversation evidence exist. |
| Drag press produced a QML argument error in an intermediate local package | The pointer was mapped through a Window with an obsolete overload. | Map the pointer to the Orb's parent item with `Qt.point`. Package revision `0.1.5-7` contains the correction; `0.1.5-6` was discarded as a local candidate. |
| Fixed positioning conflicted with saved manual coordinates | A saved manual position took precedence while the pin setting still appeared enabled. | Drag persistence now disables the pin, while enabling the pin clears manual coordinates in the same configuration update. |
| Nearby conversation could keep Voice active | The microphone level is not a valid sign of an intentional completed turn. | Idle time advances only on completed assistant transcript/speaking activity; lock and hard-limit shutdown remain independent. Privacy/product work on clearer capture visibility remains open. |
| Aggregate tests changed behavior when run on this Lenovo | Several fixtures inherited installed Codex, Maslow product branding, `NO_COLOR`, or the system Python instead of the scenario each test meant to create. One additional failure exposed stale preinstall lists after the default application set was slimmed. | Isolate host package/branding/color assumptions, run Voice with its pinned Python environment, and keep install/remove preinstall lists aligned with the shipped package list. OBS Studio, Kdenlive, and Moonlight are no longer removed as if Maslow had preinstalled them. |

## Verification completed

| Evidence | Result | Boundary |
| --- | --- | --- |
| Complete Voice Python suite in the installed pinned environment | 274 tests passed with two expected Linux namespace/isolation skips | Source and real pinned-SDK behavior; no live provider account or physical conversation |
| UI controller, UI contract, and Orb contract Node checks | Passed | State mapping, transport contract, finite geometry, shader interface, software fallback, reduced motion, drag bounds, pin/reset contract |
| Maslow brand validation | Passed | Required brand tokens and asset contracts; not subjective Orb design acceptance |
| Runtime aggregate checks | CLI suite passed; shell suite passed 245 of 246 test files | The sole failure is the intentional cross-repository Snapper coverage because no `maslow-os-iso` checkout exists on this laptop; runtime and package Snapper sections passed |
| Package repository check | `bash test/maslow-packaging` passed | Recipe structure and downstream package contract |
| Package build and install | `maslow-voice 0.1.5-7` installed; user service active | Exact local package above; no signed/public distribution |
| Running desktop visual inspection | Bottom-right idle Orb rendered through the installed package; a saved mid-screen location rendered, survived service restart, and reset to the prior bottom-right pin | Directly observed on this Lenovo; physical pointer drag itself still needs the person's test |
| Installed QML log inspection | No `Panel.qml` type, reference, or syntax error from package `0.1.5-7` | Does not prove every future interaction or display topology |
| Independent agent reviews | Runtime history, docs, Orb interaction, configuration validation, and package targeting reviewed; no remaining concrete source blocker reported | Review evidence, not hardware acceptance |

The branch is a cumulative product integration rather than a narrow Orb change. Before this checkpoint documentation and final integration cleanup, it was 91 commits and 204 changed files ahead of runtime `main` at `ae1041b4095637a2490674637e8b04cc8a4f565f`. It includes onboarding, Hub integration, slimmer fresh defaults, Maslow branding, the complete Voice stack, Gemini Live, direct peer-agent routing, and the Orb work. The package branch is a coordinated cumulative Voice/Hub package integration targeting its product branch `maslow`. Pull-request descriptions must state this full scope.

## Remaining work

### Voice UX and Orb design

1. Have the user physically drag the installed Orb, click it from ready and failed-readiness states, and exercise long press, compact controls, reset, and the bottom-right pin.
2. Inspect idle, connecting, listening, thinking/working, speaking, muted, error, and disabled states at both 56 and 88 pixels on the installed GPU path and software fallback. Record reduced-motion and at least one display resize or scale change.
3. Refine the palette and internal forms with the Maslow design system. The blue glass direction is acceptable for the current checkpoint, while the random-looking internal lines and exact color balance are explicitly unfinished.
4. Decide the persistent capture/privacy signal and how easily a person can tell when ambient speech is being recorded.
5. Keep one action to talk. Settings remain available for setup and recovery, not as a mandatory step before every conversation.

### Conversation and agent acceptance

1. Run a real Gemini conversation on the Lenovo and record first-audible latency, interruption, transcript quality, idle/lock behavior, and clean stop without exposing conversation content or credentials.
2. Run separate explicit tasks for Codex and Hermes, then Claude when configured. Verify original words, selected project, selected agent and reason, run identity, approvals, final path, and artifact contents.
3. Repeat one spoken task containing a critical filename or exact value. The prior `result.html` versus `result.H` failure remains relevant until a correction/review interaction prevents the wrong artifact.
4. Compare Gemini, GPT-Live, and LiveKit Expressive with the same bounded script and measured provider usage before making cost or smoothness claims. LiveKit Expressive remains acceptance-pending.
5. Test the `review` policy as the conservative product option and `lab_auto` as the exploratory option. Neither is a substitute for agent sandboxing or OS-level secret isolation.

### Delivery and release

1. Runtime [pull request 12](https://github.com/letsgomaslow/maslow-os/pull/12) merged to `main` as `8a0ac0af156be0b0acb780140da1fb538e228829`.
2. Package [pull request 3](https://github.com/letsgomaslow/maslow-os-pkgs/pull/3) then merged to `maslow` as `49c5741eceea8de089a901ec9919689daabbc580`.
3. Rebuild from those exact merged runtime/package commits if a release candidate is authorized. Do not publish, sign, promote, or describe a stable Maslow package channel from this source integration. Fresh install, installed update/rollback, ISO assembly, and itemized Lenovo acceptance remain separate gates.

## Documentation map and next action

- [Maslow Voice architecture and setup](../maslow-voice.md) is the current product reference.
- [Gemini Live and Voice Lab](../../voice/docs/gemini-live.md) owns provider-specific behavior and verification boundaries.
- [Voice plugin UI](../../voice/ui/README.md) owns Orb material, controls, movement, and preview instructions.
- [Voice development and verification](../../agents/skills/voice-development.md) owns the required implementation and acceptance procedure.
- [September 14 consolidated Voice checkpoint](2026-09-14-voice-checkpoint.md) preserves the older GPT-Live and LiveKit evidence.
- [September 16 Lenovo failure handoff](2026-09-16-lenovo-voice-development-handoff.md) preserves the pre-fix report and source-backup evidence.

Next action after source integration: the user physically tests Orb dragging and one Gemini conversation on this Lenovo, followed by one explicit Codex or Hermes task with artifact inspection. Keep those as three separately recorded gates.
