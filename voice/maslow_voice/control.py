"""One-shot and duplex watch client used by the native shell and Hub."""

import asyncio
import json
import sys

from .config import runtime_directory
from .errors import VoiceError
from .ipc import MAX_REQUEST, MAX_RESPONSE


async def connect():
    path = runtime_directory() / "control.sock"
    try:
        return await asyncio.open_unix_connection(str(path), limit=MAX_RESPONSE + 1)
    except (FileNotFoundError, ConnectionRefusedError):
        # A user service is the sole daemon owner. This does not capture audio.
        process = await asyncio.create_subprocess_exec("systemctl", "--user", "start", "maslow-voice.service",
                                                       stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(process.wait(), 15)
        if process.returncode == 0:
            for _ in range(20):
                try:
                    return await asyncio.open_unix_connection(str(path), limit=MAX_RESPONSE + 1)
                except (FileNotFoundError, ConnectionRefusedError):
                    await asyncio.sleep(0.1)
        raise VoiceError("VOICE_NOT_RUNNING", "Voice could not start. Check its installation in Hub.") from None


async def run(watch=False):
    reader, writer = await connect()
    try:
        if watch:
            writer.write(b'{"action":"watch"}\n')
            await writer.drain()
            async def input_loop():
                while True:
                    line = await asyncio.to_thread(sys.stdin.buffer.readline, MAX_REQUEST + 1)
                    if not line:
                        return
                    if len(line) > MAX_REQUEST:
                        raise VoiceError("REQUEST_TOO_LARGE", "The Voice request is too large.")
                    writer.write(line)
                    await writer.drain()
            async def output_loop():
                while line := await reader.readline():
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
            tasks = [asyncio.create_task(input_loop()), asyncio.create_task(output_loop())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            data = sys.stdin.buffer.readline(MAX_REQUEST + 1)
            if not data or len(data) > MAX_REQUEST:
                raise VoiceError("INVALID_REQUEST", "Send one JSON Voice request on standard input.")
            writer.write(data.rstrip(b"\n") + b"\n")
            await writer.drain()
            # Downloads and initial local inference can legitimately take minutes.
            response = await reader.readline()
            if not response:
                raise VoiceError("VOICE_DISCONNECTED", "Voice disconnected before responding.")
            sys.stdout.buffer.write(response)
            sys.stdout.buffer.flush()
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    try:
        if sys.argv[1:] not in ([], ["--watch"]):
            raise VoiceError("INVALID_ARGUMENT", "Use --watch or send one JSON request on standard input.")
        asyncio.run(run(sys.argv[1:] == ["--watch"]))
    except (VoiceError, OSError, TimeoutError) as error:
        safe = error.as_dict() if isinstance(error, VoiceError) else {"code": "VOICE_UNAVAILABLE", "message": "The local Voice service is unavailable."}
        print(json.dumps({"ok": False, "error": safe}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
