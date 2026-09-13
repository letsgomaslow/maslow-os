# Provider integration

The daemon creates one provider with `create_provider(config, secrets, emit, submit, audio_transport)` and calls `start(audio=...)` only after an explicit user session-start action. It attaches the original user transcript, project, and session metadata after `submit`; providers receive and return only the constrained intent schema.

`audio_transport` must provide async `start(handler)`, `stop()`, `play(PcmFrame)`, `clear_playback()`, and `set_muted(bool)`. `PortAudioTransport` is the default physical implementation. A future trusted offline PCM bridge can implement the same surface without exposing PipeWire to an untrusted executor.

Secrets remain daemon-owned: `openai`, or `livekit_key` and `livekit_secret`; `server_token` is sent only to the configured loopback model service. Local mode uses the daemon's `server_kind`, `server_url`, `model`, and `speech_directory`. That directory must contain the explicit `whisper-base.en` directory and `en_US-ljspeech-medium.onnx` Piper model. This layer neither downloads models nor executes a submitted intent.

Piper remains a separate GPL executable and is never imported into the daemon. The default voice is the LJSpeech medium model (LJSpeech metadata is MIT and its underlying dataset is public-domain), not a Lessac research-license voice.
