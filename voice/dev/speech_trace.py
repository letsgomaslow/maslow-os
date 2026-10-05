"""Trace a real Gemini voice session through a fake sound card.

Development diagnostic for speech that stops mid-sentence. The microphone is
silent and the speaker is consumed at real-time speed, so playback timing,
gaps and interruptions behave as on the device without opening audio
hardware. Desktop actions are stubbed with a fixed delay; nothing opens.

    PYTHONPATH=voice /usr/lib/maslow-voice/venv/bin/python voice/dev/speech_trace.py out.wav "Open github.com and tell me about pull requests"

Each argument is one step, run in order:
  <text>                 typed as the person's next turn (25 s are allowed for the reply)
  notice@<seconds>       send a finished-job update to the conversation after that delay
  load@<delay>,<seconds> load every CPU core twice over for <seconds>, starting after <delay>

It uses the Google AI Studio key saved for Voice and a temporary state
directory, consumes a little Gemini usage, and prints a timeline: state
changes, actions, speaker sound/silence, interruptions and final replies.
The WAV holds everything the speaker played. Typed turns are not spoken
turns: Gemini may plan actions differently when it hears a person.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import wave
from pathlib import Path

T0 = time.monotonic()
EVENTS = []


def log(*args):
    EVENTS.append((round(time.monotonic() - T0, 2), *args))


class FakeStream:
    """A sounddevice stream stand-in that runs the callback at real-time pace."""

    def __init__(self, samplerate, blocksize, channels, dtype, device, callback):
        self.rate, self.block, self.callback = samplerate, blocksize, callback
        self.latency = (0.02, 0.02)
        self.running = False
        self.out = bytearray()
        self.audible = False

    def start(self):
        self.running = True
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        period = self.block / self.rate
        tick = time.monotonic()
        while self.running:
            indata, outdata = bytes(self.block * 2), bytearray(self.block * 2)
            try:
                self.callback(indata, outdata, self.block, None, None)
            except TypeError:
                self.callback(outdata, self.block, None, None)
            self.out += outdata
            audible = any(outdata[i] or outdata[i + 1] for i in range(0, len(outdata), 64))
            if audible != self.audible:
                self.audible = audible
                log("speaker", "sound" if audible else "silence")
            tick += period
            time.sleep(max(0, tick - time.monotonic()))

    def stop(self):
        self.running = False

    close = stop


STREAMS = []


def stream(**options):
    STREAMS.append(FakeStream(**options))
    return STREAMS[-1]


sys.modules["sounddevice"] = types.SimpleNamespace(RawStream=stream, RawOutputStream=stream)

from maslow_voice.daemon import VoiceService  # noqa: E402  (after the fake sound card)


async def main(output, steps):
    with tempfile.TemporaryDirectory() as temp:
        service = VoiceService(Path(temp) / "state", Path(temp) / "runtime")

        async def open_slowly(application, url=None, **options):
            log("action", f"open {application} {url or ''}".strip())
            await asyncio.sleep(1.5)
            log("action", f"{application} opened")
            return {"application": application, "status": "opened", "verification": "window_observed"}
        service.desktop.open = open_slowly

        original = service.provider_event

        async def watch(event):
            kind = event.get("type")
            if kind == "voice_state":
                log("state", event.get("state"))
            elif kind == "transcript" and event.get("role") == "assistant" and event.get("final", True):
                log("said", str(event.get("text", ""))[:160])
            elif kind == "interrupted":
                log("INTERRUPTED")
            elif kind in {"error", "closed"}:
                log(kind, event.get("code", ""))
            return await original(event)
        service.provider_event = watch

        await service.start_voice(audio=True)
        await service.provider.mute(True)
        for step in steps:
            if step.startswith("notice@"):
                async def notice(delay=float(step[7:])):
                    await asyncio.sleep(delay)
                    log("notice", await service.conversation_notice({
                        "task": 'The task "flight search"', "state": "finished",
                        "guidance": "Tell the person this in a few spoken sentences, leading with the answer.",
                        "answer": "The cheapest flight is 337 dollars on Alaska, leaving Friday at 7am."}))
                service.background(notice())
            elif step.startswith("load@"):
                async def load(delay=float(step[5:].split(",")[0]), seconds=float(step[5:].split(",")[1])):
                    await asyncio.sleep(delay)
                    log("cpu load start")
                    busy = f"import time\nend = time.time() + {seconds}\nwhile time.time() < end: pass"
                    processes = [subprocess.Popen([sys.executable, "-c", busy]) for _ in range(2 * (os.cpu_count() or 1))]
                    for process in processes:
                        await asyncio.to_thread(process.wait)
                    log("cpu load end")
                service.background(load())
            else:
                log("typed", step[:80])
                await service._dispatch({"action": "submit_text", "text": step})
                await asyncio.sleep(25)
        await service.end_voice()
        service.store.close()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(48000)
        recording.writeframes(bytes(STREAMS[0].out) if STREAMS else b"")
    for event in EVENTS:
        if event[1] != "state" or event[2] in {"speaking", "thinking"}:
            print(*event)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2:]))
