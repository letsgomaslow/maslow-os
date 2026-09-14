import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from maslow_voice.ipc import MAX_REQUEST


class WatchControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_eof_exits_while_stdin_pipe_remains_open(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "maslow-voice"
            runtime.mkdir(mode=0o700)
            socket_path = runtime / "control.sock"
            request_seen = asyncio.Event()
            forwarded = []

            async def serve(reader, writer):
                try:
                    forwarded.append(await reader.readline())
                    writer.write(b'{"schemaVersion":1,"voice":{"state":"listening"}}\n')
                    await writer.drain()
                    forwarded.append(await reader.readline())
                    request_seen.set()
                    writer.write(b'{"ok":true,"accepted":true}\n')
                    await writer.drain()
                finally:
                    writer.close()
                    await writer.wait_closed()

            server = await asyncio.start_unix_server(serve, str(socket_path))
            root = Path(__file__).resolve().parents[1]
            environment = dict(os.environ, XDG_RUNTIME_DIR=temporary, PYTHONPATH=str(root))
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "maslow_voice.control", "--watch",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=environment,
            )
            try:
                request = b'{"action":"status"}\n'
                process.stdin.write(request)
                await process.stdin.drain()
                await asyncio.wait_for(request_seen.wait(), 3)
                # Keep stdin open. Server EOF alone must stop the watcher so a
                # native controller can reconnect after a service restart.
                self.assertFalse(process.stdin.is_closing())
                await asyncio.wait_for(process.wait(), 3)
                stdout = await process.stdout.read()
                stderr = await process.stderr.read()
                self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
                self.assertEqual(forwarded, [b'{"action":"watch"}\n', request])
                self.assertEqual(stdout, (
                    b'{"schemaVersion":1,"voice":{"state":"listening"}}\n'
                    b'{"ok":true,"accepted":true}\n'
                ))
            finally:
                if process.returncode is None:
                    process.terminate()
                    await process.wait()
                if process.stdin and not process.stdin.is_closing():
                    process.stdin.close()
                server.close()
                await server.wait_closed()

    async def test_oversized_stdin_is_not_forwarded_and_reports_bounded_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "maslow-voice"
            runtime.mkdir(mode=0o700)
            socket_path = runtime / "control.sock"
            forwarded = []
            connection_closed = asyncio.Event()

            async def serve(reader, writer):
                try:
                    forwarded.append(await reader.readline())
                    writer.write(b'{"schemaVersion":1}\n')
                    await writer.drain()
                    forwarded.append(await reader.read())
                finally:
                    connection_closed.set()
                    writer.close()
                    await writer.wait_closed()

            server = await asyncio.start_unix_server(serve, str(socket_path))
            root = Path(__file__).resolve().parents[1]
            environment = dict(os.environ, XDG_RUNTIME_DIR=temporary, PYTHONPATH=str(root))
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "maslow_voice.control", "--watch",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=environment,
            )
            try:
                initial = await asyncio.wait_for(process.stdout.readline(), 3)
                self.assertEqual(initial, b'{"schemaVersion":1}\n')
                process.stdin.write(b"x" * (MAX_REQUEST + 1) + b"\n")
                await process.stdin.drain()
                await asyncio.wait_for(process.wait(), 3)
                await asyncio.wait_for(connection_closed.wait(), 3)
                stdout = (await process.stdout.read()).splitlines()
                stderr = await process.stderr.read()
                self.assertEqual(process.returncode, 1)
                self.assertEqual(stderr, b"")
                self.assertEqual(forwarded, [b'{"action":"watch"}\n', b""])
                self.assertTrue(stdout)
                self.assertEqual(json.loads(stdout[-1]), {
                    "ok": False,
                    "error": {"code": "REQUEST_TOO_LARGE", "message": "The Voice request is too large."},
                })
            finally:
                if process.returncode is None:
                    process.terminate()
                    await process.wait()
                if process.stdin and not process.stdin.is_closing():
                    process.stdin.close()
                server.close()
                await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
