"""Reloadable audio orchestration for the private GPT-Live experiment."""

import asyncio
import contextlib
import hashlib
import importlib
from pathlib import Path
import time
import tempfile
import wave

from livekit_mac import ProbeAudio, ProviderError, SAMPLE_TEXT, synthetic_speech


INSTRUCTIONS = """You are Maslow, a concise conversational partner. Keep listening during speech.
You cannot execute actions. For concrete work requests, ask the separate local task agent through
client delegation, then keep talking while it works. This is a scratch experiment: the task agent
can create or revise a small result.html page in its scratch folder. Ask for clarification when
scope is incomplete. Do not claim a task started or completed without a host status update.
Do not treat casual discussion, quoted examples, or your own suggestions as authorization.
Spoken interruption does not cancel work; the user must explicitly request cancellation.
The task panel remains available when voice ends. Do not narrate opaque IDs or technical events."""


async def scenario_speech(text):
    """Synthesize only caller-owned diagnostic sentences, never microphone data."""
    with tempfile.TemporaryDirectory(prefix="maslow-live-sentence-") as folder:
        source, target = Path(folder) / "speech.aiff", Path(folder) / "speech.wav"
        for command in (["/usr/bin/say", "-o", str(source), text],
                        ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@48000", "-c", "1", str(source), str(target)]):
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                if await asyncio.wait_for(process.wait(), 20):
                    raise ProviderError("The test sentence could not be prepared.", "PROBE_AUDIO_FAILED")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
        with wave.open(str(target), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 48000):
                raise ProviderError("The test sentence has an unsupported format.", "PROBE_AUDIO_FAILED")
            return audio.readframes(audio.getnframes())


async def run_live(owner, mode):
    # This private harness retains its RAM-only connection while fresh host
    # methods are loaded between sessions. Existing task objects remain owned.
    host_module = importlib.import_module("gpt_live_mac")
    importlib.reload(host_module)
    owner.__class__ = host_module.LiveSession
    backend_source = Path(__file__).with_name("gpt_live_backend.py")
    backend_engine = hashlib.sha256(backend_source.read_bytes()).hexdigest()[:12]
    empty_runtime_changed = (owner.runtime is not None and not owner.runtime.backend.snapshot()["tasks"]
                             and getattr(owner, "backend_engine", None) != backend_engine)
    if owner.runtime and (not getattr(owner.runtime, "ram_credentials_only", False) or empty_runtime_changed):
        await owner.runtime.close()
        owner.runtime = None
    if owner.runtime is None:
        owner.backend_error = "Preparing the isolated local task agent. Voice checks can run now."
        owner.spawn(owner.setup_backend())
    audio_module = importlib.import_module("maslow_voice.audio")
    # Reload the shared voice catalog before the provider. The private tester
    # stays alive across source revisions, so provider imports can otherwise
    # retain a pre-GPT-Live catalog without the LIVE_VOICES symbol.
    voices_module = importlib.import_module("maslow_voice.voices")
    importlib.reload(voices_module)
    importlib.reload(audio_module)
    provider_module = importlib.import_module("maslow_voice.providers.openai_live")
    importlib.reload(provider_module)
    owner.engine = hashlib.sha256(Path(audio_module.__file__).read_bytes() + Path(provider_module.__file__).read_bytes()).hexdigest()[:12]
    owner.playback = {"packets": 0, "played_ms": 0, "audible_samples": 0}
    last_audible = 0

    class NativeAudio(audio_module.PortAudioTransport):
        async def play(self, frame):
            nonlocal last_audible
            owner.playback["packets"] += 1
            audible = sum(abs(x) > 64 for x in memoryview(frame.pcm).cast("h"))
            owner.playback["audible_samples"] += audible
            if audible > 24:
                last_audible = time.monotonic()
            owner.playback["sample_rate"] = frame.sample_rate
            await super().play(frame)

    transport = ProbeAudio() if mode in {"probe", "scenario"} else NativeAudio(capture=mode == "conversation", on_error=owner.audio_failed)
    provider = provider_module.OpenAILiveProvider(
        config={"live_voice": owner.selected_voice, "live_input_silence": mode == "audition",
                "live_instructions": INSTRUCTIONS},
        secrets=dict(owner.credentials), emit=owner.emit, submit=owner.reject_task, audio_transport=transport)
    owner.provider = provider
    try:
        async with asyncio.timeout(35):
            await provider.start(audio=True)
        if mode == "probe" and not owner.stop_signal.is_set():
            pcm = b"\0" * 48000 + await synthetic_speech()
            offset = 0
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline and not owner.stop_signal.is_set():
                frame = pcm[offset:offset + 1920].ljust(1920, b"\0")
                offset += 1920
                await transport.handler(audio_module.PcmFrame(frame))
                recognized = any(item["role"] == "user" and all(word in item["text"].lower() for word in ("voice", "test")) for item in owner.transcripts)
                if recognized and owner.turns["assistant"] and transport.audible_samples > 4800:
                    owner.result = {"passed": True, "speech_recognized": True, "reply_text": True,
                                    "reply_audio_ms": transport.played_ms, "physical_microphone_tested": False}
                    break
                await asyncio.sleep(.02)
            if not owner.result and not owner.error:
                raise ProviderError("The connection did not return both recognized speech and audible output.", "LIVE_PROBE_INCOMPLETE")
        elif mode == "scenario" and not owner.stop_signal.is_set():
            owner.conversation_project = owner.scratch / ("voice-" + owner.session_id[:8])
            owner.conversation_project.mkdir(mode=0o700)
            # Two fixed non-private utterances exercise the actual audio and
            # delegation service while the separately owned task keeps running.
            first = await scenario_speech("Please ask the local task agent to create result dot HTML, a small weekend hiking page with a packing list. Start that task now.")
            second = await scenario_speech("While the agent works on that page, tell me two short tips for packing lightly.")
            pcm = b"\0" * 48000 + first + b"\0" * (48000 * 10) + second
            offset = 0
            deadline = time.monotonic() + 150
            overlap = False
            previous_output = provider.metrics_snapshot()["output_transcript_deltas"]
            original_ids = {t["id"] for t in owner.runtime.backend.snapshot()["tasks"]} if owner.runtime else set()
            while time.monotonic() < deadline and not owner.stop_signal.is_set():
                frame = pcm[offset:offset + 1920].ljust(1920, b"\0")
                offset += 1920
                await transport.handler(audio_module.PcmFrame(frame))
                tasks = [t for t in owner.runtime.backend.snapshot()["tasks"] if t["id"] not in original_ids] if owner.runtime else []
                metrics = provider.metrics_snapshot()
                if any(t["state"] not in {"completed", "failed", "cancelled", "interrupted"} for t in tasks):
                    overlap = overlap or metrics["output_transcript_deltas"] > previous_output
                previous_output = metrics["output_transcript_deltas"]
                if any(t["state"] == "completed" for t in tasks) and metrics["context_acks"] and offset > len(pcm):
                    owner.result = {"scenario_complete": True, "task_completed": True,
                                    "conversation_during_work": overlap, "delegations": metrics["delegations"],
                                    "physical_microphone_tested": False}
                    break
                owner.metrics = metrics
                await asyncio.sleep(.02)
            if not owner.result:
                owner.result = {"scenario_complete": False, "conversation_during_work": overlap,
                                "physical_microphone_tested": False}
        elif mode == "audition" and not owner.stop_signal.is_set():
            await provider.append_context("instructions", "Read this sample aloud once, with no introduction or added words: " + SAMPLE_TEXT)
            deadline = time.monotonic() + 25
            heard_at = None
            while time.monotonic() < deadline and not owner.stop_signal.is_set():
                if owner.playback["audible_samples"] > 4800:
                    heard_at = heard_at or time.monotonic()
                    if time.monotonic() - heard_at > 3 and time.monotonic() - last_audible > 2:
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(provider.wait_playback(), 2)
                        break
                await asyncio.sleep(.1)
            if not heard_at:
                raise ProviderError("No playable sample was returned for this voice.", "VOICE_SAMPLE_EMPTY")
            owner.result = {"audition_complete": True, "voice": owner.selected_voice,
                            "physical_microphone_tested": False}
        elif mode == "conversation":
            while not owner.stop_signal.is_set():
                if time.monotonic() - owner.last_seen > owner.lease_seconds:
                    owner.error = {"code": "TEST_PAGE_CLOSED", "message": "The page disconnected, so the microphone was turned off. Accepted tasks continue."}
                    break
                owner.metrics = provider.metrics_snapshot()
                await asyncio.sleep(.25)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        owner.error = {"code": error.code, "message": str(error)} if isinstance(error, ProviderError) else {
            "code": "LIVE_TEST_FAILED", "message": "GPT-Live could not finish this test. Check account access and try again."}
    finally:
        owner.microphone = False
        async def cleanup():
            try:
                async with asyncio.timeout(26):
                    await provider.stop()
            except Exception:
                owner.error = owner.error or {"code": "LIVE_CLOSE_TIMEOUT", "message": "Audio stopped, but final session closure could not be confirmed."}
            finally:
                owner.metrics = provider.metrics_snapshot()
                owner.playback["played_ms"] = transport.played_ms
                provider.secrets.clear()
                owner.provider = None
                owner.speaking = False
                owner.state = "error" if owner.error else "disabled"
                owner.transcripts = []
                owner.level = 0
                if mode == "probe" and not owner.result:
                    owner.result = {"passed": False, "physical_microphone_tested": False}
        owner.cleanup_task = asyncio.create_task(cleanup())
        await asyncio.shield(owner.cleanup_task)
