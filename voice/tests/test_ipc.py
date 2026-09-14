import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from maslow_voice.ipc import ControlServer


class ControlServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_disconnects_open_watcher_before_waiting_for_server(self):
        with tempfile.TemporaryDirectory() as temporary:
            socket_path = Path(temporary) / "control.sock"
            control = ControlServer(
                socket_path,
                lambda request: None,
                lambda: {"schemaVersion": 1},
                peer_check=lambda writer: True,
            )
            await control.start()
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            try:
                writer.write(b'{"action":"watch"}\n')
                await writer.drain()
                self.assertEqual(json.loads(await reader.readline()), {"schemaVersion": 1})

                await asyncio.wait_for(control.close(), 1)

                self.assertEqual(await asyncio.wait_for(reader.read(), 1), b"")
                self.assertFalse(socket_path.exists())
                self.assertEqual(control.connections, set())
                self.assertEqual(control.watchers, set())
            finally:
                writer.close()
                await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
