# Private Mac cloud Voice tests

This development-only tester runs the production LiveKit Expressive or OpenAI Realtime provider and, after an explicit Start talking action, the production PortAudio transport. It does not start the Linux daemon, expose its Unix control socket, send tasks to Hermes, or replace Quickshell acceptance.

Use an existing Python 3.11+ environment containing `voice/requirements.txt` dependencies. From the runtime repository root:

```bash
PYTHONPATH=voice python voice/dev/livekit_mac.py
```

For OpenAI, run a separate tester process; the LiveKit page can keep its existing connection in memory:

```bash
PYTHONPATH=voice python voice/dev/livekit_mac.py --provider openai
```

The OpenAI page accepts only an OpenAI API key and uses the production `gpt-realtime-2.1` default. It offers Cedar, Marin, Alloy, Ash, Ballad, Coral, Echo, Sage, Shimmer, and Verse. Each test creates a new session with the selected voice because OpenAI locks the voice after the first audio output. Preview voice opens only speakers and asks the Realtime model to read the fixed comparison sample; wording is model-generated and may vary. It uses Realtime audio, not the separate text-to-speech endpoint or LiveKit Expressive. The [official voice and conversation guide](https://developers.openai.com/api/docs/guides/realtime-conversations#voice-options) lists the supported voices and recommends Marin and Cedar for quality.

Open the printed `http://127.0.0.1:<port>` address on the same Mac. Enter the three values from one LiveKit project and select Save connection. Never put these values in command arguments, shell history, chat, test fixtures, screenshots, or source control. The form clears all three inputs after saving; the provider credentials remain only in the local tester process's memory. Clear saved connection removes them. Stopping the tester also removes them. Closing the browser page ends an active audio conversation but does not terminate the tester process or erase its saved connection.

Check connection uses macOS `say` and `afconvert` to prepare one fixed synthetic sentence in a temporary directory. LiveKit feeds that sentence through the actual room, speech recognition, language model, Expressive TTS, and returned RTC audio; OpenAI uses the actual Realtime WebSocket provider with 24 kHz PCM and input transcription. Neither opens physical audio devices. Success requires a recognized user transcript containing “voice” and “test,” a final assistant transcript, and non-silent returned PCM. These checks consume the selected provider account's API usage. They do not prove physical microphone operation, audible speaker quality, echo cancellation, or latency during a real conversation.

Start talking requests native audio access on the Mac. Allow the macOS microphone prompt for the process's responsible app if presented. Speak, listen, interrupt a reply, and then select End conversation. Report observed response quality separately from the synthetic connection result. The authenticated page heartbeat expires after eight seconds without activity; loss of the page stops capture. End is idempotent and preserves owned shutdown work. Each test clears its transient transcript on completion.

The LiveKit voice chooser offers a curated English comparison set: Ashley, Edward, Olivia, Alex, and Dennis. Preview voice sends the same fixed sentence to the selected Inworld TTS 2 voice and opens only the speaker via the production transport's `capture=False` path. It does not open a native microphone. Stop audio ends a sample or conversation. Start talking uses the currently selected voice in the normal Expressive conversation. Tester selection remains in memory. The separate Linux settings use saved `livekit_voice` and `realtime_voice` preferences; tester choices do not write those settings.

Voice names are drawn from the [LiveKit Inworld guide](https://docs.livekit.io/agents/models/tts/inworld/), the [current Inworld catalog schema/example](https://docs.inworld.ai/api-reference/voiceAPI/voiceservice/list-voices), and its [legacy voice example](https://docs.inworld.ai/api-reference/ttsAPI/texttospeech/list-voices). The legacy endpoint is not called. LiveKit documents support for Inworld default voices; these five are a comparison subset, not a complete dynamically queried catalog. The current LiveKit Python inference SDK has no voice-listing method. Inworld's full catalog requires separate Inworld authentication, which this tester does not request.

The server binds only loopback, validates Host/Origin and an in-memory request nonce, disables caching and third-party resources, and never returns account details in status. `/status` exposes only safe state, audio packet-size counters, engine source digest, and test results. Received PCM duration includes silence; it is not answer duration. Transcript access is separately authenticated. Third-party SDK/native output is discarded because diagnostic text may contain credentials or endpoints. Do not enable raw debug logging with real account values. Unexpected live failures should be diagnosed with safe error classes, codes, and bounded counters.

The tester reloads the local audio and selected provider modules between sessions. This permits focused implementation retests while keeping the account details in the same RAM-only owner. Reloading is a development feature, not part of the installed Linux runtime. `--port <number>` can preserve a known loopback address when the tester itself must restart, but process restart still clears its credentials. Run only one physical conversation or preview at a time when both provider pages are open.

Boundary tests use no cloud account or physical audio:

```bash
PYTHONPATH=voice:voice/dev python -m unittest discover -s voice/dev -p 'test_*.py'
```

Keep this directory outside the installed Voice payload. This tester requires neither a new dependency nor a change to the production Linux security boundary.

## GPT-Live conversation and task experiment

Use the separate private Mac experiment to test full-duplex conversation with an independently owned task runner:

```bash
PYTHONPATH=voice python voice/dev/gpt_live_mac.py --port 57519
```

This uses the actual `gpt-live-1` WebSocket endpoint, client delegation, continuous PCM input, and Maslow's existing native playback. The curated picker includes Marin, Cedar, and the additional voices listed in the [Live conversation guide](https://developers.openai.com/api/docs/guides/live-conversations). It does not replace the production Realtime provider or change the Linux provider setting. LiveKit Expressive remains a separate option.

Save the OpenAI key in this page; it stays in the tester's memory and the task subprocess environment. The local Hermes planner and scratch executor use `gpt-5-mini` through that same OpenAI account. Each runs with an isolated temporary home, no model tools, no inherited account settings, and a Mac write sandbox. Hermes returns a bounded JSON artifact; the host validates and writes only the approved scratch file. This is a deliberately limited test of independent agent execution, not a proof of general coding-tool routing, the Hermes HTTP Runs API, or a formal A2A protocol exchange.

Check connection sends a fixed synthetic sentence without opening the microphone. Start talking opens native microphone and speakers. Test voice handoff sends two fixed synthetic utterances, asking for a scratch page and continuing an unrelated conversation while work runs. A context acknowledgment proves injection acceptance, not that the user heard a spoken completion. Returned PCM duration includes silence. Listening and speaking are independent states.

GPT-Live emits transcript deltas and an opaque delegation ID; it does not emit a final task instruction. The host coalesces fragments, then the separate planner receives role-labelled context and current task state. It must choose a new task, correction, explicit cancellation, or clarification. A pause alone never grants execution authority. Task IDs, revisions, duplicate suppression, and cancellation remain host responsibilities.

Typed requests use the same task backend. Redirect stops and reaps the previous scratch attempt before incrementing the same task's attempt. Cancelled, unchanged, or stale outputs cannot publish a new artifact. Stop audio and page disappearance stop voice while accepted work remains owned by the tester. Clear connection and stop test tasks ends both; stopping the tester also ends its owned workers. Scratch artifacts remain available for inspection. The task database and isolated Hermes home are temporary; persistence across tester restarts is not established by this experiment.

The private `/view` endpoint includes transient conversation and task details; the public `/status` contains only bounded counters and safe state. Never save raw microphone audio, account values, or raw third-party diagnostics as evidence. Record synthetic task artifact checks, safe metrics, and the user's physical audio feedback separately. The native orb, installed Linux adapter, general app/coder execution, and Lenovo acceptance require their own later validation.
