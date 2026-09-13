"""Private, bounded local control channel. No TCP control listener."""

import asyncio
import json
import os
import socket
import stat
import struct

from .errors import VoiceError

MAX_REQUEST = 65536
MAX_RESPONSE = 4 * 1024 * 1024


def peer_is_owner(writer):
    sock = writer.get_extra_info("socket")
    if hasattr(socket, "SO_PEERCRED"):
        _pid, uid, _gid = struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        return uid == os.getuid()
    # Linux is the supported production host; other platforms are test-only.
    return False


def remove_stale_socket(path):
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise VoiceError("UNSAFE_SOCKET", "Voice's local connection path is not a private socket.")
        path.unlink()


class ControlServer:
    def __init__(self, path, dispatch, snapshot, *, peer_check=peer_is_owner):
        self.path, self.dispatch, self.snapshot, self.peer_check = path, dispatch, snapshot, peer_check
        self.watchers = set()
        self.connections = set()
        self.server = None

    async def start(self):
        remove_stale_socket(self.path)
        self.server = await asyncio.start_unix_server(self._connection, str(self.path), limit=MAX_REQUEST + 1)
        self.path.chmod(0o600)

    @staticmethod
    async def send(writer, value):
        data = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        if len(data) > MAX_RESPONSE:
            raise VoiceError("RESPONSE_TOO_LARGE", "Voice history is too large to display.")
        writer.write(data)
        await asyncio.wait_for(writer.drain(), 3)

    async def publish(self):
        if not self.watchers:
            return
        snapshot = self.snapshot()
        async def deliver(writer):
            try:
                await self.send(writer, snapshot)
            except (OSError, TimeoutError, VoiceError):
                self.watchers.discard(writer)
                writer.close()
        await asyncio.gather(*(deliver(writer) for writer in tuple(self.watchers)))

    async def _connection(self, reader, writer):
        self.connections.add(writer)
        try:
            if not self.peer_check(writer):
                return
            while True:
                try:
                    line = await reader.readline()
                    if not line:
                        break
                    if len(line) > MAX_REQUEST:
                        raise VoiceError("REQUEST_TOO_LARGE", "The Voice request is too large.")
                    request = json.loads(line)
                    if not isinstance(request, dict):
                        raise ValueError()
                    if request == {"action": "watch"}:
                        self.watchers.add(writer)
                        await self.send(writer, self.snapshot())
                    else:
                        result = await self.dispatch(request)
                        await self.send(writer, {"ok": True, **(result or {})})
                except VoiceError as error:
                    await self.send(writer, {"ok": False, "error": error.as_dict()})
                except (ValueError, UnicodeError, asyncio.LimitOverrunError):
                    await self.send(writer, {"ok": False, "error": {"code": "INVALID_REQUEST", "message": "Voice requires a valid, bounded JSON request."}})
                    break
                except Exception:
                    await self.send(writer, {"ok": False, "error": {"code": "CONTROL_FAILED", "message": "Voice could not complete this action. Check its setup and try again."}})
        except (OSError, TimeoutError):
            pass
        finally:
            self.watchers.discard(writer)
            self.connections.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for writer in tuple(self.connections):
            writer.close()
        self.path.unlink(missing_ok=True)
