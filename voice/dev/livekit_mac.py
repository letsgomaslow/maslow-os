"""Private, development-only cloud Voice probe and native Mac audio test.

Run with PYTHONPATH=voice using the Voice provider environment. No credentials,
captured audio, or transcripts are written to disk. This is not the Linux IPC
server and must never be packaged or exposed beyond loopback.
"""

import asyncio
import argparse
import contextlib
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import secrets
import tempfile
import time
import wave

from aiohttp import web

from maslow_voice.audio import PcmFrame
from maslow_voice.config import validate_endpoint
from maslow_voice.errors import VoiceError
from maslow_voice.providers.base import ProviderError
from maslow_voice.providers.livekit_expressive import LiveKitExpressiveProvider
from maslow_voice.voices import OPENAI_VOICES

VOICES = [
    {"name": "Ashley", "language": "English (US)"},
    {"name": "Edward", "language": "English (US)"},
    {"name": "Olivia", "language": "English (UK)"},
    {"name": "Alex", "language": "English"},
    {"name": "Dennis", "language": "English"},
]
SAMPLE_TEXT = "Hi, I'm Maslow. We can think through an idea together, or turn it into a clear plan. What would you like to work on?"


class ProbeAudio:
    """Feed known synthetic speech; count replies without opening audio devices."""

    def __init__(self):
        self.handler = None
        self.received_samples = 0
        self.received_ms = 0
        self.audible_samples = 0
        self.muted = False

    async def start(self, handler):
        self.handler = handler

    async def stop(self):
        self.handler = None

    async def set_muted(self, muted):
        self.muted = muted

    async def play(self, frame):
        self.received_samples += len(frame.pcm) // 2
        self.received_ms += len(frame.pcm) * 500 / frame.sample_rate
        self.audible_samples += sum(abs(value) > 64 for value in memoryview(frame.pcm).cast("h"))

    async def clear_playback(self):
        pass

    async def wait_playback(self):
        pass

    @property
    def played_ms(self):
        return int(self.received_ms)


async def synthetic_speech(text="Hello Maslow. Please say that the voice test is working."):
    # Only a fixed, non-private test sentence touches these temporary files.
    with tempfile.TemporaryDirectory(prefix="maslow-synthetic-") as folder:
        source, target = Path(folder) / "speech.aiff", Path(folder) / "speech.wav"
        for command in (
            ["/usr/bin/say", "-o", str(source), text],
            ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@48000", "-c", "1", str(source), str(target)],
        ):
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.DEVNULL,
                                                           stderr=asyncio.subprocess.DEVNULL)
            try:
                async with asyncio.timeout(20):
                    if await process.wait():
                        raise ProviderError("The Mac could not prepare the test sentence.", "PROBE_AUDIO_FAILED")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
        with wave.open(str(target), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 48000):
                raise ProviderError("The test audio format is unsupported.", "PROBE_AUDIO_FAILED")
            return audio.readframes(audio.getnframes())


class Session:
    def __init__(self, provider_factory=None, *, kind="livekit"):
        if kind not in {"livekit", "openai"}:
            raise ValueError("Unsupported test provider")
        self.kind = kind
        self.label = "OpenAI Realtime" if kind == "openai" else "LiveKit"
        self.voices = [{"name": name, "language": "Realtime"} for name in OPENAI_VOICES] if kind == "openai" else VOICES
        self.provider_factory = provider_factory
        self.credentials = {}
        self.url = ""
        self.job = None
        self.provider = None
        self.stop_signal = asyncio.Event()
        self.state = "disabled"
        self.microphone = False
        self.error = None
        self.mode = None
        self.result = None
        self.transcripts = []
        self.turns = {"user": 0, "assistant": 0}
        self.level = 0
        self.last_seen = time.monotonic()
        self.lease_seconds = 8
        self.end_lock = asyncio.Lock()
        self.cleanup_task = None
        self.engine = ""
        self.playback = {}
        self.selected_voice = "cedar" if kind == "openai" else "Ashley"
        self._partial = {}

    def status(self):
        return {"ready": bool(self.credentials), "busy": bool(self.job and not self.job.done()),
                "state": self.state, "microphone": self.microphone, "error": self.error,
                "mode": self.mode, "result": self.result, "turns": self.turns, "level": self.level,
                "engine": self.engine, "playback": self.playback,
                "selected_voice": self.selected_voice, "voices": self.voices, "provider": self.kind}

    async def emit(self, event):
        kind = event.get("type")
        if kind == "voice_state":
            self.state = event["state"]
            self.microphone = bool(event["microphone"] and self.mode == "conversation")
        elif kind == "error":
            # Provider messages/codes are sanitized at the production boundary.
            self.error = {"code": event["code"], "message": event["message"]}
            self.microphone = False
            self.stop_signal.set()
        elif kind == "transcript":
            role = event.get("role")
            if role in self.turns:
                # Streaming deltas update one visible turn; a final transcript
                # replaces them, rather than duplicating words and turn counts.
                item = self._partial.get(role)
                final = event.get("final", True)
                value = str(event.get("text", ""))[:4000]
                if item is None:
                    item = {"role": role, "text": ""}
                    self.transcripts.append(item)
                item["text"] = value if final else (item["text"] + value)[:4000]
                if final:
                    self.turns[role] += 1
                    self._partial.pop(role, None)
                else:
                    self._partial[role] = item
                self.transcripts = self.transcripts[-16:]
        elif kind == "level":
            self.level = event["level"]

    async def audio_failed(self):
        await self.emit({"type": "error", "code": "AUDIO_UNAVAILABLE",
                         "message": "Microphone or speaker access stopped. Check Mac microphone permission and try again."})

    async def reject_task(self, _intent, _turn):
        raise ProviderError("This conversation test does not send work to other agents.", "TEST_ONLY")

    def save(self, body):
        if self.status()["busy"]:
            raise ProviderError("End the current test before changing the connection.", "TEST_BUSY")
        if self.kind == "openai":
            if (not isinstance(body, dict) or set(body) != {"key"}
                    or not isinstance(body["key"], str) or not body["key"].strip()
                    or len(body["key"]) > 4096 or any(c.isspace() for c in body["key"].strip())):
                raise ProviderError("Paste your OpenAI API key in the private field.", "INVALID_SETUP")
            self.credentials = {"openai": body["key"].strip()}
            self.error = None
            self.result = None
            return
        if not isinstance(body, dict) or set(body) != {"url", "key", "secret"}:
            raise ProviderError("Enter all three LiveKit fields.", "INVALID_SETUP")
        if any(not isinstance(value, str) or not value.strip() or len(value) > 4096 for value in body.values()):
            raise ProviderError("Enter all three LiveKit fields.", "INVALID_SETUP")
        url = validate_endpoint(body["url"].strip(), livekit=True)
        self.credentials = {"livekit_key": body["key"].strip(), "livekit_secret": body["secret"].strip()}
        self.url = url
        self.error = None
        self.result = None

    def start(self, mode, voice=None):
        if not self.credentials:
            raise ProviderError("Save your OpenAI API key first." if self.kind == "openai" else "Save the three LiveKit fields first.", "SETUP_REQUIRED")
        if self.status()["busy"]:
            raise ProviderError("A test is already running.", "TEST_BUSY")
        if voice is not None:
            if not isinstance(voice, str) or voice not in {item["name"] for item in self.voices}:
                raise ProviderError("Choose one of the available sample voices.", "INVALID_VOICE")
            self.selected_voice = voice
        self.stop_signal = asyncio.Event()
        self.mode, self.error, self.result = mode, None, None
        self.transcripts = []
        self._partial.clear()
        self.turns = {"user": 0, "assistant": 0}
        self.state, self.microphone = "connecting", False
        self.last_seen = time.monotonic()
        self.cleanup_task = None
        self.job = asyncio.create_task(self.run(mode))

    async def run(self, mode):
        # Reload only between sessions, allowing provider fixes to be retested
        # without moving account values to disk or restarting this private form.
        audio_module = importlib.import_module("maslow_voice.audio")
        provider_module = importlib.import_module("maslow_voice.providers." + ("openai_realtime" if self.kind == "openai" else "livekit_expressive"))
        if self.provider_factory is None:
            importlib.reload(audio_module)
            importlib.reload(provider_module)
        self.engine = hashlib.sha256(Path(audio_module.__file__).read_bytes() + Path(provider_module.__file__).read_bytes()).hexdigest()[:12]
        self.playback = {"packets": 0, "packet_samples": {}, "played_ms": 0, "audible_samples": 0}
        owner = self
        class NativeAudio(audio_module.PortAudioTransport):
            async def play(self, frame):
                samples = len(frame.pcm) // 2
                owner.playback["packets"] += 1
                owner.playback["audible_samples"] += sum(abs(value) > 64 for value in memoryview(frame.pcm).cast("h"))
                sizes = owner.playback["packet_samples"]
                sizes[str(samples)] = sizes.get(str(samples), 0) + 1
                owner.playback["sample_rate"] = frame.sample_rate
                owner.playback["device_callback_samples"] = self.blocksize
                owner.playback["played_ms"] = self.played_ms
                await super().play(frame)
        transport = ProbeAudio() if mode == "probe" else NativeAudio(capture=mode != "audition", on_error=self.audio_failed)
        factory = self.provider_factory or getattr(provider_module, "OpenAIRealtimeProvider" if self.kind == "openai" else "LiveKitExpressiveProvider")
        config = {"mode": self.kind, "livekit_url": self.url, "livekit_voice": self.selected_voice,
                  "realtime_voice": self.selected_voice}
        provider = factory(config=config,
                                         secrets=dict(self.credentials), emit=self.emit,
                                         submit=self.reject_task, audio_transport=transport)
        self.provider = provider
        try:
            async with asyncio.timeout(50):
                await provider.start(audio=True)
            if mode == "probe" and not self.stop_signal.is_set():
                pcm = await synthetic_speech()
                # Silence gives the STT endpoint time to finish the known turn.
                pcm = b"\0" * 48000 + pcm + b"\0" * 48000 * 6
                for offset in range(0, len(pcm), 1920):
                    if self.stop_signal.is_set():
                        break
                    await transport.handler(PcmFrame(pcm[offset:offset + 1920].ljust(1920, b"\0")))
                    await asyncio.sleep(.02)
                async with asyncio.timeout(40):
                    while not self.stop_signal.is_set():
                        recognized = any(item["role"] == "user" and all(word in item["text"].lower() for word in ("voice", "test")) for item in self.transcripts)
                        if recognized and self.turns["assistant"] and transport.audible_samples > 4800:
                            self.result = {"passed": True, "speech_recognized": True, "reply_text": True,
                                           "reply_audio_ms": transport.played_ms, "physical_microphone_tested": False}
                            break
                        await asyncio.sleep(.1)
            elif mode == "audition" and not self.stop_signal.is_set():
                # The same exact text provides a fair voice comparison. Agent
                # sessions still use Expressive mode for real conversations.
                async with asyncio.timeout(45):
                    if self.kind == "openai":
                        await provider.text("Read this voice comparison sample aloud exactly, with no introduction or added words: " + SAMPLE_TEXT)
                    else:
                        await provider._session.say(SAMPLE_TEXT)
                # RTC also sends silence after speech. Drain the native tail
                # with a bound so that continuous silence cannot hold preview.
                with contextlib.suppress(TimeoutError):
                    async with asyncio.timeout(15 if self.kind == "openai" else 1):
                        if self.kind == "openai":
                            await provider.wait_playback()
                        else:
                            await transport.wait_playback()
                if not self.error:
                    if self.playback["audible_samples"] < 4800:
                        raise ProviderError("This voice did not return a playable sample. Try another voice or preview again.", "VOICE_SAMPLE_EMPTY")
                    self.result = {"audition_complete": True, "voice": self.selected_voice,
                                   "physical_microphone_tested": False}
            elif mode == "conversation":
                while not self.stop_signal.is_set():
                    if time.monotonic() - self.last_seen > self.lease_seconds:
                        self.error = {"code": "TEST_PAGE_CLOSED", "message": "The test page disconnected, so the microphone was turned off."}
                        break
                    try:
                        await asyncio.wait_for(self.stop_signal.wait(), .5)
                    except TimeoutError:
                        pass
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            self.error = {"code": self.kind.upper() + "_TEST_TIMEOUT", "message": self.label + " did not finish the connection or spoken reply in time."}
        except Exception as error:
            safe = error if isinstance(error, ProviderError) else (
                LiveKitExpressiveProvider._public_error(error) if self.kind == "livekit" else
                ProviderError("OpenAI could not complete the test. Check the connection and try again.", "OPENAI_TEST_FAILED"))
            self.error = {"code": safe.code, "message": str(safe)}
        finally:
            self.microphone = False
            self.playback["played_ms"] = transport.played_ms
            self.cleanup_task = asyncio.create_task(self.cleanup(provider, mode))
            await asyncio.shield(self.cleanup_task)

    async def cleanup(self, provider, mode):
        try:
            async with asyncio.timeout(15):
                await provider.stop()
        except Exception:
            self.error = self.error or {"code": "TEST_CLEANUP_FAILED", "message": "The test could not finish closing. Restart the private tester."}
        finally:
            provider.secrets.clear()
            self.provider = None
            self.state = "error" if self.error else "disabled"
            self.microphone = False
            self.transcripts = []
            self._partial.clear()
            self.level = 0
            if mode == "probe" and not self.result:
                self.result = {"passed": False, "physical_microphone_tested": False}

    async def end(self):
        async with self.end_lock:
            self.stop_signal.set()
            if self.job and not self.job.done():
                if self.cleanup_task is None:
                    self.job.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.shield(self.job)
            if self.cleanup_task:
                await asyncio.shield(self.cleanup_task)
            self.microphone = False
            self.transcripts = []
            self._partial.clear()


SESSION = web.AppKey("session", Session)
ORIGIN = web.AppKey("origin", str)
TOKEN = web.AppKey("token", str)


def create_app(session=None, *, page_path=None):
    @web.middleware
    async def private_boundary(request, handler):
        origin = request.app[ORIGIN]
        if request.host != origin.removeprefix("http://"):
            raise web.HTTPForbidden(text="Use the private loopback address.")
        if request.method != "GET" or request.path == "/view":
            if request.headers.get("Origin", origin if request.method == "GET" else "") != origin:
                raise web.HTTPForbidden(text="This action must come from the private tester.")
            if not secrets.compare_digest(request.headers.get("X-Maslow-Test", ""), request.app[TOKEN]):
                raise web.HTTPForbidden(text="Reload the private tester.")
        try:
            response = await handler(request)
        except (ProviderError, VoiceError) as error:
            response = web.json_response({"error": {"code": error.code, "message": str(error)}}, status=400)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = web.json_response({"error": {"code": "INVALID_REQUEST", "message": "The form could not be read."}}, status=400)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                                 "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-" + request.app[TOKEN] + "'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"})
        return response

    app = web.Application(middlewares=[private_boundary], client_max_size=16384)
    app[SESSION] = session or Session()
    app[ORIGIN] = "http://127.0.0.1:0"
    app[TOKEN] = secrets.token_urlsafe(32)

    async def index(request):
        page = (Path(page_path) if page_path else Path(__file__).with_suffix(".html")).read_text()
        return web.Response(text=page.replace("__NONCE__", app[TOKEN]).replace("__PROVIDER__", app[SESSION].kind), content_type="text/html")

    async def status(request):
        return web.json_response(app[SESSION].status())

    async def view(request):
        app[SESSION].last_seen = time.monotonic()
        private_view = getattr(app[SESSION], "private_view", None)
        return web.json_response(private_view() if private_view else app[SESSION].transcripts)

    async def action(request):
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType()
        body = await request.json()
        name = request.match_info["name"]
        session = app[SESSION]
        if name == "save":
            session.save(body)
        elif name in {"probe", "conversation", "audition"}:
            if not isinstance(body, dict) or set(body) - {"voice"}:
                raise ProviderError("The voice selection could not be read.", "INVALID_REQUEST")
            session.start(name, body.get("voice"))
        elif name == "end":
            await session.end()
        elif name == "forget":
            await session.end()
            clear_connection = getattr(session, "clear_connection", None)
            if clear_connection:
                await clear_connection()
            session.credentials.clear()
            session.url = ""
            session.result = None
        elif getattr(session, "extra_action", None):
            await session.extra_action(name, body)
        else:
            raise web.HTTPNotFound()
        return web.json_response({"ok": True})

    async def cleanup(_app):
        await app[SESSION].end()
        app[SESSION].credentials.clear()
        app[SESSION].url = ""
        shutdown = getattr(app[SESSION], "shutdown", None)
        if shutdown:
            await shutdown()

    app.router.add_get("/", index)
    app.router.add_get("/status", status)
    app.router.add_get("/view", view)
    app.router.add_post("/action/{name}", action)
    app.on_cleanup.append(cleanup)
    return app


async def main(port=0, provider="livekit"):
    # Third-party SDK logs can contain endpoints. Keep only our bounded, safe
    # status visible; never persist their raw logs in this credentialed test.
    logging.disable(logging.CRITICAL)
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda _loop, _context: None)
    app = create_app(Session(kind=provider))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    app[ORIGIN] = f"http://127.0.0.1:{port}"
    print(app[ORIGIN], flush=True)
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--provider", choices=("livekit", "openai"), default="livekit")
    arguments = parser.parse_args()
    try:
        asyncio.run(main(arguments.port, arguments.provider))
    except KeyboardInterrupt:
        pass
