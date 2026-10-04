"""Short, microphone-free Gemini Live voice samples; no tools or saved state."""

import asyncio
import re

from .audio import PcmFrame, PortAudioTransport

SAMPLE = "Hello, I'm Maslow. I can help you think things through and get things done."
VOICES = ("Puck", "Zephyr", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
          "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
          "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
          "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
          "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat")


async def play_sample(settings, key, voice, playing, *, transport_factory=PortAudioTransport, client_factory=None):
    from google import genai
    from google.genai import types

    client = (client_factory or genai.Client)(api_key=key, vertexai=False)
    transport = transport_factory(capture=False, speaker_device=settings.get("speaker_device"))
    heard = False

    async def discard(_frame):
        pass

    try:
        async with asyncio.timeout(25):
            await transport.start(discard)
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
                system_instruction="Read the supplied voice sample exactly once. Do not add any other words.",
            )
            async with client.aio.live.connect(model=settings["gemini_live_model"], config=config) as session:
                await session.send_client_content(turns=types.Content(role="user", parts=[types.Part(text=SAMPLE)]), turn_complete=True)
                async for message in session.receive():
                    content = message.server_content
                    turn = content.model_turn if content else None
                    for part in (turn.parts or []) if turn else []:
                        blob = part.inline_data
                        if blob and blob.data:
                            match = re.fullmatch(r"audio/pcm;rate=(\d+)", blob.mime_type or "")
                            if not match or int(match[1]) not in {16000, 24000, 48000}:
                                raise ValueError("Unsupported preview audio format")
                            if not heard:
                                heard = True
                                await playing()
                            await transport.play(PcmFrame(blob.data, int(match[1])))
                if not heard:
                    raise ValueError("Preview returned no audio")
                await transport.wait_playback()
                await asyncio.sleep(transport.output_latency_seconds)
    finally:
        try:
            await transport.stop()
        finally:
            await client.aio.aclose()
