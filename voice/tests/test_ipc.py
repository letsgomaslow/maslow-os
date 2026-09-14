import asyncio
import json
import socket
import tempfile
import unittest
from pathlib import Path

from maslow_voice.ipc import ControlServer, MAX_RESPONSE


class ControlServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_watcher_gets_latest_snapshot_without_blocking_publish_or_fast_watcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            socket_path = Path(temporary) / "control.sock"
            state = {"revision": 0}
            control = ControlServer(
                socket_path,
                lambda request: None,
                lambda: dict(state),
                peer_check=lambda writer: True,
            )
            await control.start()
            clients = []
            try:
                for _ in range(2):
                    reader, writer = await asyncio.open_unix_connection(
                        str(socket_path), limit=MAX_RESPONSE + 1,
                    )
                    writer.write(b'{"action":"watch"}\n')
                    await writer.drain()
                    self.assertEqual(json.loads(await reader.readline()), {"revision": 0})
                    clients.append((reader, writer))
                    if len(clients) == 1:
                        slow_server_writer = next(iter(control.watchers))
                        slow_server_writer.get_extra_info("socket").setsockopt(
                            socket.SOL_SOCKET, socket.SO_SNDBUF, 4096,
                        )

                slow_reader, _slow_writer = clients[0]
                fast_reader, _fast_writer = clients[1]
                state["payload"] = "x" * (512 * 1024)
                max_senders = 0
                for revision in range(1, 11):
                    state["revision"] = revision
                    await asyncio.wait_for(control.publish(), .2)
                    max_senders = max(max_senders, len(control._watch_senders))
                    fast = json.loads(await asyncio.wait_for(fast_reader.readline(), 1))
                    self.assertEqual(fast["revision"], revision)

                slow_revisions = []
                while not slow_revisions or slow_revisions[-1] != 10:
                    snapshot = json.loads(await asyncio.wait_for(slow_reader.readline(), 2))
                    slow_revisions.append(snapshot["revision"])
                    self.assertLessEqual(len(slow_revisions), 10)
                self.assertLess(len(slow_revisions), 10)
                self.assertLessEqual(max_senders, 2)

                for _ in range(100):
                    if slow_server_writer not in control._watch_senders:
                        break
                    await asyncio.sleep(0)
                self.assertNotIn(slow_server_writer, control._watch_senders)

                # Gate one watcher at the same send boundary as a full socket,
                # then prove shutdown reaps that sole sender without waiting
                # for the client to drain or the production timeout to elapse.
                send_started = asyncio.Event()
                never_release = asyncio.Event()
                original_send = control.send
                async def gated_send(writer, value):
                    if writer is slow_server_writer:
                        send_started.set()
                        await never_release.wait()
                    await original_send(writer, value)
                control.send = gated_send
                state["revision"] = 11
                await asyncio.wait_for(control.publish(), .2)
                fast = json.loads(await asyncio.wait_for(fast_reader.readline(), 1))
                self.assertEqual(fast["revision"], 11)
                await asyncio.wait_for(send_started.wait(), 1)
                self.assertIn(slow_server_writer, control._watch_senders)
                await asyncio.wait_for(control.close(), 1)
                self.assertEqual(control._watch_senders, {})
                self.assertEqual(control._watch_pending, {})
            finally:
                for _reader, writer in clients:
                    writer.close()
                    await writer.wait_closed()
                if control.server is not None:
                    await control.close()

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
