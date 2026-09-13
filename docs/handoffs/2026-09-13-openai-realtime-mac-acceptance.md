# OpenAI Realtime Mac acceptance

The user confirmed the LiveKit voice auditions worked and requested that both providers' voice choices be included in the next update. Their next priority is actual OpenAI Realtime testing on this Mac before any update preparation or publication. This supersedes the next action in the [LiveKit checkpoint](2026-09-13-livekit-mac-acceptance.md), while retaining its audio fix and evidence.

## Scope and delivery

Work continues on `codex/livekit-setup` in `/Users/r.david/.codex/worktrees/maslow-voice/livekit-runtime`, based on `c814d417`. The frozen unsigned Hub 0.3.1 / Voice 0.1.3 candidate and published Hub 0.3.0 staging sequence 4 are unchanged. No dependency, package, signing, publication, ISO, or Lenovo change is part of this checkpoint. The previously reported flat orb remains queued after provider acceptance.

Scoped local commits: `475bfe031a9e1b602a21403b236b39b06d58fcab` contains saved cloud voices, native pickers, and production OpenAI fixes; `2dfe0df5cc67a8e68af18855f46e248762216059` contains the private OpenAI tester. Neither is pushed or packaged. The user has been asked to test microphone speech and interrupt a reply; no physical-conversation feedback has arrived at this checkpoint. Leave the test page available and reuse its saved RAM-only key.

The existing loopback tester now accepts `--provider openai`. A separate process at `http://127.0.0.1:57518/` preserves the working LiveKit process at `http://127.0.0.1:57517/`. Both use `/tmp/maslow-voice-providers.jHhHnl/bin/python` and retain credentials only in RAM. The user entered the OpenAI key privately. Never read its form, memory, clipboard, request body, or raw provider logs into chat or evidence. Status endpoints exclude keys and transcripts.

The OpenAI page offers all ten built-in Realtime voices, with speaker-only previews, synthetic speech checks, and explicit native microphone conversations. Each test uses a fresh production provider session. OpenAI locks the voice after initial audio output. The selected production model remains `gpt-realtime-2.1`, verified in the [official model documentation](https://developers.openai.com/api/docs/models/gpt-realtime-2.1). Cedar and Marin are recommended by the [official voice guide](https://developers.openai.com/api/docs/guides/realtime-conversations#voice-options). OpenAI Realtime uses its own speech generation; LiveKit Expressive remains specific to the LiveKit path.

Linux settings now save `realtime_voice` (default Cedar) and `livekit_voice` (default Ashley), validate against the shared catalog, and show the corresponding native picker. Both pickers disable during an active conversation. Existing connection-change handling ends the provider session; the next Start uses the saved voice. The LiveKit picker follows the three credential fields and Save action so first-time setup remains visible at 1280×800.

## Defects and fixes

An independent provider review identified cancellation and shutdown defects: cancelled startup skipped cleanup, device-stop failure could leave the reader/socket alive, and awaiting native playback inside the WebSocket reader blocked interruption processing during output backpressure. A bounded separate audio delivery worker now keeps socket handling responsive, suppresses cancelled response audio, and uses playback duration within the current assistant item for truncation. Manual VAD response handling now disables server-side auto-cancellation to avoid redundant client/server cancellation. Failed or incomplete response completion is a failure, not a successful conversation result. Errors classify safe authentication, usage, setup, identifier, protocol, and service failures without reflecting raw diagnostics.

Live testing isolated a separate preview defect: the speech-input probe passed, but the API rejected `item.id` on a typed preview before returning audio. The original generated identifier contained `item_` plus 32 hexadecimal UUID characters. The replacement keeps all 128 bits in a 32-character hexadecimal UUID and preserves that same identity across the submitted message, emitted transcript, and response metadata. The identical Cedar preview then returned and played audio successfully. Official docs did not establish a 32-character limit, so the evidence supports this concrete rejection/fix rather than a general published length claim.

Streaming transcript deltas now update a single visible tester turn, with the final transcript replacing partial text. Saving credentials never starts audio. The production `capture=False` speaker path is reused for previews; synthetic probes open no physical audio devices.

Audio state now remains Speaking after generation completes until queued output reaches the speaker. The drain wait runs independently of the socket reader and checks session generation/response identity so interruption, a new reply, or Stop cannot be overwritten by an old completion.

## Evidence

Evidence root: `/Users/r.david/.codex/visualizations/2026/09/13/01a09a02-5898-7873-8684-032cf60f9165/`.

- `openai-voice/live/cloud-probe-cedar.json`: real OpenAI synthetic speech check passed with one recognized user turn, one final assistant turn, and 3,900 ms returned PCM. No microphone or speaker was opened. Engine digest `926a022978d9`.
- `openai-voice/live/preview-message-id-rejected.json`: real native preview failed with safe `OPENAI_ITEM_ID_INVALID`, zero returned audio, engine `926a022978d9`.
- `openai-voice/live/preview-cedar-passed.json`: after the identifier fix, Cedar returned 19 packets at 24 kHz, 111,181 non-silent samples, and 7,550 ms native playback. Microphone remained off. Engine `35cb4f9a0889`. These counters prove returned/rendered PCM; subjective quality requires the user's listening report.
- `openai-voice/live/preview-marin-passed.json`: Marin returned 18 packets at 24 kHz, 116,712 non-silent samples, and 7,150 ms native playback, with no error and microphone off. Same engine as the Cedar preview. These two live previews preceded the final speaking-state drain fix; that fix has focused automated coverage and loads at the next new session.
- `livekit-setup/ui/livekit-voice-final.png` and `openai-voice-picker.png`: actual Quickshell captures at 1280×800, inspected by the worker and coordinator. The intermediate `livekit-voice-picker.png` pushed Save below view and was rejected; the final source moves voice choice after setup. Owned preview container was stopped afterward.
- The OpenAI browser form was inspected before private key entry. Only its safe status and controls are inspected after entry. No private speech, account identifiers, room identifiers, keys, or raw audio are retained in evidence.
- Final complete Voice suite: 144 tests discovered, 142 passed and two Linux namespace tests skipped on macOS. Fifteen private tester tests passed without account calls or audio devices; Node UI contracts and `git diff --check` passed. The new provider cases cover startup cancellation, shutdown failure, restart/unmute, safe failures, backpressure/VAD, cancelled deltas, per-item truncation, typed identifier identity, and speaking-state drain cancellation. An initial integration test expected immediate synchronous playback; it was updated to await actual delivery and retained its PCM/interrupt assertions.

## Next gate

Finish native voice previews and obtain the user's microphone/speaker and interruption feedback. Preserve keys in the running testers while provider fixes reload between sessions. Do not claim physical audio quality, installed Linux acceptance, or Lenovo operation from the synthetic probe or test counts. After provider acceptance, finish the queued orb work, then prepare a coordinated replacement candidate and use the existing installed QEMU/TCG and signed Hub OTA workflow.
