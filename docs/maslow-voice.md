# Maslow Voice

Maslow Voice is an optional, consent-led conversational coordinator for Maslow AI-OS. The conversation provider can answer normally or emit one validated work brief; it cannot run commands, open applications, approve requests, or execute coding work. The daemon binds each brief to the captured user turn, selected project, mode, and original words, then routes the persisted task to Codex, Hermes, or Claude through a separate execution boundary.

Current status: the source tree contains an unpublished staging candidate whose default conversation path is Gemini 3.8 Live. Local package `0.1.5-7` is installed on the Lenovo development laptop and its service, glass Orb, saved movement, restart persistence, reset and QML loading were directly inspected. Physical pointer drag, a real Gemini conversation, selected-agent artifact completion, the full Lenovo acceptance matrix, package promotion, stable-channel publication and a verified-ISO rebuild remain open. Use the [September 19 integration handoff](handoffs/2026-09-19-gemini-voice-orb-integration.md), [development index](maslow-development.md) and [Voice testing guide](../agents/skills/voice-development.md) when preparing acceptance.

## Installed experience

`maslow.voice` is a kept-loaded Quickshell panel plugin. Its single Orb stays at bottom right when idle with no outstanding tasks, moves to bottom center during a conversation, and moves to bottom left while tasks need attention, including when Voice is disabled. A configured idle Orb is colored and announced as ready. One short click starts listening immediately; it opens Advanced Voice settings only when conversation readiness needs attention. A press-and-hold opens Advanced Voice settings directly.

The Orb can be dragged inside 16-pixel display margins. Its normalized location persists across Voice service restarts and display-size changes. Dragging turns off the bottom-right pin; enabling **Keep orb at bottom right** clears the manual location in the same update. **Reset orb position** returns to automatic state-driven placement.

The current material is a blue glass sphere with three curved internal sheets, asymmetric white/ice reflection, and restrained Maslow teal and purple accents. `VoiceOrb.frag` is the normal GPU path. A Canvas glass treatment and deep-blue gradient base preserve visibility with software rendering or a failed shader pipeline. `MASLOW_VOICE_GPU_SHADER=0` forces the fallback for verification. Reduced motion freezes both paths. The current blue direction is functional; the internal forms, exact palette, movement and distinctive Maslow personality remain design work. See the [Voice plugin UI reference](../voice/ui/README.md), [Orb contract](../voice/tests/orb-contract-test.mjs), and [UI contract](../voice/tests/ui-contract-test.mjs).

During a conversation the orb exposes a compact strip with the current state, microphone state, Mute or Resume, End, Captions, Tasks, and Settings. Closing the full controller leaves the compact controls, orb, conversation, and independent task state in place. The shell lock path hides the controls and ends the live voice session. A conversation also ends after the configured interval without a completed conversational turn while Maslow is not speaking, and every session has a hard 30-minute maximum. Raw microphone energy does not extend the session.

These are the implemented placement/lifecycle rules. Fast fixture-driven Quickshell renders and installed position/persistence/reset inspection cover part of them; the complete real installed UI flow, physical drag, every state at 56 and 88 pixels, software/GPU comparison and display-resize behavior have not been accepted.

The panel has Talk, Type, Tasks, and Advanced Voice settings pages. Tasks expose status, one-request approval or denial, steering where the selected executor supports it, cancellation, continuation, dismissal, and the offline review/export flow. `omarchy-launch-voice [talk|type|tasks|settings]` summons the existing shell plugin. If Voice is not installed, the launcher opens Hub's Voice page instead. The default desktop binding is `Super+Shift+V`.

Hub's Voice page is the installation and readiness entry point. It reads a reduced status snapshot through `omarchy-voice-control`, opens the Voice plugin, and launches package installation in a visible terminal. Hub does not receive or store Voice credentials.

## Conversation modes

The selected mode is strict. Missing dependencies, credentials, models, or connectivity produce a visible error; Voice never falls back to another provider.

| Mode | Conversation path | Setup and execution notes |
| --- | --- | --- |
| Maslow Voice (`gemini_live`) | Gemini 3.8 Live through the LiveKit Agents Google realtime plugin, connected directly to Google AI Studio. The local native audio path owns microphone capture, acoustic processing, speaker playback, interruption, and cleanup; Gemini supplies native audio replies, transcription, and realtime turn detection. | Save a Google AI Studio API key in Secret Service. This mode does not join a LiveKit room and does not consume the saved LiveKit project URL, API key, or API secret. Those room credentials remain available for optional LiveKit Expressive mode. The default voice is `Puck`. |
| OpenAI Realtime (`openai`) | Direct OpenAI Realtime WebSocket using the configured model, default `gpt-realtime-2.1`; audio uses server VAD, `gpt-4o-mini-transcribe`, and the `cedar` voice | Save the OpenAI API key in the normal desktop keyring. It serves the conversation only. Task-agent readiness is reported separately. |
| GPT-Live cloud (`gpt_live`) | Full-duplex `gpt-live-1` session with continuous audio and transcript fragments, using the selected voice (default `marin`) from the 22 built-in choices in `voice/maslow_voice/voices.py` | Save the OpenAI API key in the normal desktop keyring. Client delegation is a separate event: the host builds a bounded transcript-backed brief, then sends it through the same peer task router. |
| LiveKit Expressive (`livekit`) | The native factory uses direct custom AgentSession audio I/O with local PortAudio/APM, LiveKit cloud inference, `expressive=True`, Deepgram Nova-3 STT, Gemma 4 31B inference, Inworld TTS, and local Silero turn detection | Save the project URL, API key, and API secret together with **Save LiveKit setup**. This optional mode consumes the LiveKit project credentials. Native account/audio checks require the actual packaged path. **Acceptance pending.** |
| Your model server (`server`) | Local Faster Whisper speech-to-text and Piper speech, with conversation JSON generated by a user-selected Ollama or LM Studio endpoint | Install local support, download the speech pack, choose the server type, URL, model, and optional server token. The configured execution model defaults to the conversation model when left blank. |
| Offline on this computer (`offline`) | The same local speech path, with a dedicated Ollama service inside the selected workspace's isolated runtime | Install local support, select an existing Ollama model folder and downloaded model, then pass isolated readiness and inference. LM Studio is supported only in Server mode. |

The local/server provider accepts only a JSON reply plus an optional structured intent. OpenAI Realtime, Maslow Voice, and LiveKit Expressive expose only `submit_intent`. GPT-Live uses client delegation rather than Realtime tool calls. The separate executor must clarify missing scope; transcript fragments and delegation notices are not additional permission to act.

`gemini_live` is the default only when Voice creates a new settings file. `Settings` merges saved files with defaults without replacing an existing valid `mode`, so an upgrade preserves the person's saved provider choice.

## Setup

Install cloud and model-server support with:

```bash
omarchy-install-voice
```

Install Voice plus local speech and fully offline support with:

```bash
omarchy-install-voice local
```

The equivalent routed commands are `omarchy install voice` and `omarchy install voice local`. Installation enables and starts `maslow-voice.service`, then opens Voice Settings when the desktop is unlocked and ready. If it finishes while locked, plugin refresh waits for the next explicit open after unlocking. In Settings:

1. Choose a mode in Advanced Voice settings and enter its connection settings. A new installation starts with **Maslow Voice** (`gemini_live`); an upgrade retains its saved mode. OpenAI conversation credentials are saved as the normal OpenAI key in the desktop Secret Service keyring; GPT-Live uses that same conversation key.
2. For Maslow Voice, save the Google AI Studio key. The Google key is the only provider credential consumed by the Gemini conversation. The same setup surface can retain a LiveKit project URL, API key, and API secret for optional Expressive mode; Gemini does not read or transmit those values. For LiveKit Expressive, enter the project URL, API key, and API secret together, then choose **Save LiveKit setup**. Blank credential fields retain an already-saved value; they do not erase it. Credentials are stored in the desktop Secret Service keyring, not `settings.json`, process arguments, or Hub.
3. For Server or Offline mode, install and verify the English speech pack, then select and test an existing model. Voice does not download a language model.
4. Choose Automatic routing, Codex, Claude Code, or Hermes as the default task agent. Automatic routing chooses the configured ready default first, then checks Codex, Hermes, and Claude in that fixed order without duplicates. An explicitly named unavailable agent fails visibly and is never replaced silently. Server and Offline modes can use a distinct task model. Hermes keeps its own model/profile settings and does not reuse the conversation key implicitly. Codex uses its existing configuration, while cloud Claude requires the separate Anthropic key saved for Voice.
5. For Gemini Voice Lab, choose whether an explicit work request starts automatically (`lab_auto`) or becomes a proposed task that must be reviewed and started (`review`). Both policies require an explicit work request; selecting `lab_auto` does not grant broader tool permissions or approve later Codex, Hermes, or Claude requests.
6. Use **Check connection and readiness**. The panel reports conversation readiness independently from task readiness, so a usable conversation can remain ready while a selected task agent needs setup. Then click the ready orb or submit a typed turn. A project folder is optional for conversation and requested only when delegated work requires one.

The `english-base-1` speech pack is 211,308,198 bytes and uses pinned, checksummed assets: Faster Whisper `base.en` and Piper `en_US-ljspeech-medium`. Downloads are resumable and restricted to the recorded HTTPS hosts and sizes. Local inference loads files only from the verified speech directory.

### Maslow Voice and LiveKit Expressive setup

Maslow Voice uses the LiveKit Agents runtime and Google plugin as an in-process SDK, but it does not use a LiveKit room or LiveKit Inference. `LiveKitGeminiProvider` constructs `google.realtime.RealtimeModel` with `vertexai=False`, the saved Google AI Studio key, model `gemini-3.8-live`, voice `Puck`, audio output, input/output transcription, and realtime model turn detection. The native local transport captures and plays audio directly. LiveKit room credentials are outside this provider connection.

In **Advanced Voice settings**, choose **Maslow Voice**, enter the Google AI Studio API key, and save setup. LiveKit fields on that setup surface retain the optional Expressive connection; they are not Gemini authentication fields. Choose **Check connection and readiness** to see the conversation and task sections separately, then click the ready orb to start listening.

LiveKit Expressive remains an optional, acceptance-pending mode in this staging candidate. Older Voice 0.1.2 had confirmed LiveKit session and audio wiring defects. The frozen Voice 0.1.3 / Hub 0.3.1 correction candidate and local Voice 0.1.4 packages have separate acceptance and publication records; consult the [current checkpoint](handoffs/2026-09-14-voice-checkpoint.md) before giving update commands for any previously published package.

On any computer, sign in to [LiveKit Cloud](https://cloud.livekit.io), create a project, then open its **Settings → API Keys**. Create an API key if needed and keep that same project's URL, API key and API secret available. Its URL starts with `wss://` and normally ends with `.livekit.cloud`. The project needs available LiveKit Inference usage; check its usage/billing page if the account reports a limit. Do not share the secret in chat or screenshots.

To test the optional path from source, open **Advanced Voice settings** and choose **LiveKit Expressive**:

| LiveKit value | Maslow Voice field/action |
| --- | --- |
| Project URL (`LIVEKIT_URL`) | Enter in the **Project URL** field. |
| API key (`LIVEKIT_API_KEY`) | Enter in the **API key** field. |
| API secret (`LIVEKIT_API_SECRET`) | Enter in the **API secret** field. |
| Complete setup | Choose **Save LiveKit setup**. The three values are saved as one setup; leaving either credential field blank retains its existing keyring value. |
| Voice selector | Choose among `Ashley`, `Edward`, `Olivia`, `Alex`, and `Dennis`; the default is `Ashley`. |

Choose **Check connection and readiness**. For cloud modes this checks saved fields and local prerequisites, not account authentication or working audio. Click the ready orb, then speak first. Check that your words appear and that you hear a reply; try interrupting a reply, then choose **End**. A project folder and coding-agent settings are unnecessary for this initial conversation test.

The native candidate runs AgentSession locally and uses LiveKit cloud inference without routing local microphone/playback through two room participants. No separate Cloud agent deployment is required by this implementation. Expressive Mode is enabled with `expressive=True`. Its Inworld TTS 2 / selected voice, Deepgram transcription and Gemma model use [LiveKit Inference](https://docs.livekit.io/agents/models/inference/), so this path uses the LiveKit credentials rather than separate model-provider keys. See [LiveKit's Expressive Mode documentation](https://docs.livekit.io/agents/models/tts/expressive/). Those credentials remain separate from Gemini's Google AI Studio request. Physical Lenovo behavior remains untested for both candidate cloud paths.

Source/SDK and installed-package tests do not establish a real account conversation. Record successful authentication, microphone capture, transcript, audible reply, interruption and stop on the Lenovo separately.

## Execution boundary

The conversation model never becomes the executor. A validated intent crosses to `TaskManager`, which persists an immutable task identity, `selected_agent`, and a plain-language `routing_reason`. An explicit `tool_preference` selects that peer only; if it is unavailable, submission fails visibly without falling back. For `auto`, `AgentRouter` prefers a configured ready default and then checks Codex, Hermes, and Claude in that deterministic order. A duplicate request identity returns the already persisted route without rerunning readiness or creating a second execution.

`lab_auto` starts a validated explicit request after routing. `review` persists it as `proposed`, shows the objective, project, shared context and selected agent, and requires Start. Start revalidates the same selected agent and never silently reroutes the reviewed task. These policies decide when task execution begins; they do not bypass any executor's existing per-tool approval or cancellation behavior.

Hermes receives its task through the loopback-only Hermes Runs service with an idempotency key. The dedicated Hermes profile has terminal and file tools plus three reviewed daemon tools, exposed as `maslow_delegate_coding`, `maslow_open_application`, and `maslow_open_website`. Pinned Hermes defers these schemas behind `tool_search`, `tool_describe`, and `tool_call`; their absence from the initial direct tool list is expected. The daemon tools cross a private, owner-only, authenticated Unix socket. Task status polling is authoritative; the event stream contributes bounded progress facts.

Codex and Claude can also own the top-level task directly through a `TaskManager`-compatible client backed by the existing structured adapters:

- Codex uses `codex app-server --listen stdio://`, performs the JSON-RPC handshake, starts a thread and turn, and records the returned session, thread, and turn identities. Online execution requests `workspace-write`, `untrusted` approvals, and the user reviewer.
- Claude uses `ClaudeSDKClient` in streaming mode with `permission_mode="default"` and a per-tool `can_use_tool` callback. Cloud Claude receives only the Anthropic API key saved for Voice, runs with a private temporary config directory, and does not import the user's Claude OAuth state, settings, hooks, or MCP configuration.

Codex and Claude approvals are single-request decisions tied to the Voice task, child, and approval UUID. Cancellation interrupts the active adapter and rejects pending child approvals. See [Voice execution bridge](../voice/docs/execution.md) for protocols, desktop allowlists, user-server routing, and the detailed approval contract.

Hermes run identities are durable and reconciled after daemon restart. Direct Codex and Claude jobs live in the Voice daemon and cannot be proven resumable after it exits. Any accepted, running, approval-waiting, submitting, or stopping direct job found during recovery becomes `interrupted` with `DIRECT_RUN_LOST`; Voice never resubmits it automatically. Continue is a new explicit attempt after the person reviews partial changes.

## Fully offline workspace

Offline mode creates one private copied workspace and one dedicated Ollama execution environment. Hermes runs there when selected; direct Codex or Claude uses the same isolated runtime and selected local model. Bubblewrap starts the environment with `--unshare-all`, a private network and PID/IPC namespaces, dropped capabilities, and a cleared environment. The original project is not mounted. User home, host runtime sockets, D-Bus, PipeWire, SSH agent, browser profile, and host display-control sockets are absent. Installed system and packaged agent trees are read-only; the private `/project`, home, temporary, runtime, and application-profile paths are writable. CPU inference is supported; GPU passthrough is not implemented.

Visible offline applications run against a separate trusted Weston nested compositor. Supported fixed application names are terminal, files, editor, and browser. The offline browser can open project files and private localhost previews, but the namespace has no internet access. Trusted microphone capture and playback remain outside the executor namespace; only text and structured intent cross into it.

Stopping execution preserves the private snapshot. Review requires all tasks and the runtime to be stopped, then returns a digest and exact add/modify/delete paths. Export requires that same digest and an explicit selected-path list, revalidates the stopped snapshot, and checks original-file fingerprints before writing. No model or Hermes tool can export automatically. Each selected file is replaced atomically, although a multi-file export is not one filesystem transaction. See [Fully offline workspace](../voice/docs/offline.md) for the complete mount, worker, review, conflict, and export contract.

## Service state and restart behavior

The per-user `maslow-voice.service` belongs to the graphical session, uses a private umask, restarts three seconds after failure, and stops its process group on shutdown. The controller starts the service on demand but does not capture audio until the user explicitly starts Voice. Ending Voice releases microphone/playback, invalidates current turn identities, and clears the conversation transcript; it does not cancel separately persisted tasks.

Tasks and bounded event history live in a private SQLite database under the user's Voice state directory. Hermes tasks are recovered and reconciled by their saved run ID rather than blindly resubmitted. Submission uses a stable idempotency identity. A handoff or stop that cannot be reconciled safely is marked interrupted for review. Direct Codex and Claude tasks are never reconstructed after a daemon restart; an active direct task becomes interrupted and requires an explicit Continue. Offline shutdown terminates the namespace and nested display while retaining the private project snapshot for restart, review, or export.

Hermes cold startup has a bounded two-minute readiness allowance. Dedicated profiles disable unrelated lazy dependency installation through Hermes's supported configuration; upstream security checks remain enabled. If the local coordinator is confirmed to have exited, its task becomes interrupted while retaining the prior run identity and partial work. Continue starts a new explicit attempt. Temporary connection failures alone retain reconciliation of the same run. Voice never treats a network error as permission to repeat execution.

The daemon writes a bounded private `voice-audit.jsonl` for session start/end timing, provider/model identifiers, safe error codes, task state and selected agent, and provider usage counters when supplied. It rotates between two files of about 2 MiB each and limits string fields to 200 characters. The allowlist excludes transcript text, raw audio, credentials, prompts, task source, tool arguments, and reasoning. Audit write failure never keeps the microphone open or prevents shutdown.

## Package ownership and pinned dependencies

The runtime repository owns `voice/`, `omarchy-install-voice`, `omarchy-launch-voice`, shell/menu integration, and this reference. The `maslow-os-pkgs` repository owns the two package recipes:

- `maslow-voice` owns the Python 3.14 virtual environment, daemon, controller, systemd user unit, Hermes plugin, Quickshell plugin, compiled orb shader, requirement lock, and speech/cloud/coding adapters. Required system packages include Quickshell, libsecret, PortAudio, libsndfile, and `hermes-agent>=0.21.0-2`; Codex, Claude Code, and `maslow-voice-local` remain optional packages.
- `maslow-voice-local` owns the Piper 1.8.0 runtime wrapper and adds bubblewrap, Weston, Ollama, and the dependencies for local speech and isolated workspaces. Speech and language-model files remain user state and are not package-owned.

Direct Python requirements are pinned and expanded into hash-checked lock files. The current source pins LiveKit Agents 1.8.2, LiveKit Google 1.8.2, LiveKit Silero 1.8.2, LiveKit API 1.2.1, LiveKit 1.1.18, OpenAI 2.48.0, websockets 15.0.1, Faster Whisper 1.2.1, sounddevice 0.5.6, Claude Agent SDK 0.2.152, PyYAML 6.0.3, and Piper TTS 1.8.0.

## Verification boundary

The source tests cover provider selection and intent validation, Gemini plugin construction and event handling, native audio lifecycle, one-click Orb contracts, lifecycle and task persistence, deterministic peer routing, review policy, Hermes Runs reconciliation, direct-run restart interruption, Codex and Claude adapter contracts, approvals and cancellation, local model handling, offline filesystem/export controls, bounded audit records, and the QML UI contract. Run them with:

```bash
bash test/shell.d/voice-test.sh
```

This focused runner also participates in `./test/shell`. SDK integration tests require the pinned Voice dependencies; Linux isolation tests need a kernel/container that permits the required namespaces. See the [implementation handoff](handoffs/2026-09-13-maslow-voice-implementation.md) for exact test counts, broader baseline failures, real Quickshell renders, installed packages, local speech, offline model inference/export, nested Foot interaction and actual coding-binary protocol evidence.

Specific live OpenAI/LiveKit sessions and synthetic task flows passed at the revisions recorded in the [consolidated checkpoint](handoffs/2026-09-14-voice-checkpoint.md). They do not validate this newer Gemini candidate. Remaining gates include Google AI Studio authentication on the installed package, at least 20 conversational turns, cold click-to-listening and end-of-turn latency measurements, interruption timing, a continuous ten-minute session, nearby-speech/echo/silence behavior, mute, desktop lock, the hard session cap, one real Codex task, one real Hermes task, rollback, stable-channel promotion, and itemized visual inspection on the Lenovo. GPT-Live comparison is a benchmark, not acceptance evidence for Gemini. No source test, package build, older signed staging update, or user-reported module arrival authorizes package publication, stable promotion, signing changes, or a verified-ISO rebuild.
