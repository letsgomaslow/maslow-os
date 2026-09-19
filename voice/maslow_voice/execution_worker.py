"""Claude SDK bridge launched only inside the offline namespace."""

import asyncio
import json
import sys
from pathlib import Path

# Direct script launch uses the immutable packaged source, not project imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from maslow_voice.execution import ClaudeSdkAdapter


def emit(kind, **payload):
    sys.stdout.write(json.dumps(dict(type=kind, **payload)) + "\n")
    sys.stdout.flush()


async def run():
    reader = asyncio.StreamReader(limit=2 * 1024 * 1024)
    await asyncio.get_running_loop().connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
    payload = json.loads(await reader.readline())
    sequence = 0

    async def progress(**value):
        emit("progress", value=value)

    async def approval(**value):
        nonlocal sequence
        sequence += 1
        identity = sequence
        emit("approval", id=identity, value=value)
        answer = json.loads(await reader.readline())
        if answer.get("type") != "approval" or answer.get("id") != identity or type(answer.get("allowed")) is not bool:
            raise ValueError("invalid approval")
        return answer["allowed"]

    adapter = ClaudeSdkAdapter("ollama", model=payload["model"], base_url="http://127.0.0.1:11434")
    try:
        result = await adapter.run(payload["task"], payload["child"], payload["instructions"], approval, progress)
        emit("result", value=result)
    except Exception:
        emit("error")
    finally:
        await adapter.cancel()


if __name__ == "__main__":
    asyncio.run(run())
