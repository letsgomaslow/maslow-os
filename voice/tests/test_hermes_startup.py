import asyncio
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from maslow_voice import offline_worker
from maslow_voice.coordinator import HERMES_START_TIMEOUT as ONLINE_HERMES_START_TIMEOUT
from maslow_voice.coordinator import _wait_for_hermes as wait_for_online_hermes
from maslow_voice.coordinator import _wait_for_owned_hermes
from maslow_voice.coordinator import _terminate_hermes_process_group
from maslow_voice.coordinator import HermesRuntime
from maslow_voice.coordinator import process_confirmed_dead
from maslow_voice.errors import VoiceError
from maslow_voice.offline import OfflineRuntime


class FakeProcess:
    returncode = None


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, duration):
        self.now += duration


class HermesStartupDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def run_waiter(self, kind, probe, process=None, **kwargs):
        process = process or FakeProcess()
        if kind == "online":
            return await wait_for_online_hermes(process, probe, **kwargs)
        return await offline_worker._wait_for_hermes(process, probe, **kwargs)

    async def test_both_waiters_accept_late_readiness_before_elapsed_deadline(self):
        for kind in ("online", "offline"):
            with self.subTest(kind=kind):
                clock = Clock()
                calls = 0

                async def probe():
                    nonlocal calls
                    calls += 1
                    if clock() < 1.5:
                        if kind == "online":
                            raise VoiceError("NOT_READY", "not ready")
                        raise OSError("not ready")

                await self.run_waiter(kind, probe, timeout=2, poll_interval=0.5, clock=clock, sleep=clock.sleep)
                self.assertEqual(clock(), 1.5)
                self.assertEqual(calls, 4)

    async def test_both_waiters_stop_at_one_elapsed_deadline(self):
        for kind in ("online", "offline"):
            with self.subTest(kind=kind):
                clock = Clock()

                async def probe():
                    if kind == "online":
                        raise VoiceError("NOT_READY", "not ready")
                    raise OSError("not ready")

                expected = VoiceError if kind == "online" else ValueError
                with self.assertRaises(expected) as failure:
                    await self.run_waiter(kind, probe, timeout=2, poll_interval=0.5, clock=clock, sleep=clock.sleep)
                self.assertEqual(clock(), 2)
                if kind == "online":
                    self.assertEqual(failure.exception.code, "HERMES_START_TIMEOUT")
                else:
                    self.assertEqual(str(failure.exception), "hermes timeout")

    async def test_both_waiters_fail_immediately_when_process_exits(self):
        for kind in ("online", "offline"):
            with self.subTest(kind=kind):
                called = False

                async def probe():
                    nonlocal called
                    called = True

                process = FakeProcess()
                process.returncode = 1
                expected = VoiceError if kind == "online" else ValueError
                with self.assertRaises(expected) as failure:
                    await self.run_waiter(kind, probe, process=process)
                self.assertFalse(called)
                if kind == "online":
                    self.assertEqual(failure.exception.code, "HERMES_START_FAILED")
                else:
                    self.assertEqual(str(failure.exception), "hermes start failed")

    async def test_both_waiters_propagate_cancellation_without_retrying(self):
        for kind in ("online", "offline"):
            with self.subTest(kind=kind):
                started = asyncio.Event()

                async def probe():
                    started.set()
                    await asyncio.Event().wait()

                waiting = asyncio.create_task(self.run_waiter(kind, probe))
                await started.wait()
                waiting.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(waiting, 0.1)

    async def test_online_cancellation_kills_owned_parent_and_grandchild(self):
        with tempfile.TemporaryDirectory() as root:
            sentinel = Path(root) / "grandchild-survived"
            grandchild_code = (
                "import time; from pathlib import Path; time.sleep(0.5); "
                f"Path({json.dumps(str(sentinel))}).write_text('survived')"
            )
            parent_code = (
                "import subprocess,sys,time; "
                f"child=subprocess.Popen([sys.executable,'-c',{json.dumps(grandchild_code)}]); "
                "print(child.pid,flush=True); time.sleep(60)"
            )
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "-c", parent_code,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
            await asyncio.wait_for(process.stdout.readline(), 2)
            started = asyncio.Event()

            async def probe():
                started.set()
                await asyncio.Event().wait()

            waiting = asyncio.create_task(_wait_for_owned_hermes(process, probe))
            try:
                await started.wait()
                waiting.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(waiting, 2)
                self.assertIsNotNone(process.returncode)
                await asyncio.sleep(0.7)
                self.assertFalse(sentinel.exists())
            finally:
                waiting.cancel()
                await asyncio.gather(waiting, return_exceptions=True)
                if process.returncode is None:
                    await _terminate_hermes_process_group(process, force=True)

    async def test_offline_parent_allows_worker_deadline_and_cleanup_margin(self):
        self.assertEqual(ONLINE_HERMES_START_TIMEOUT, 120)
        self.assertEqual(offline_worker.HERMES_START_TIMEOUT, 120)
        with tempfile.TemporaryDirectory() as root:
            plugin = Path(root) / "plugin"
            plugin.mkdir()
            for name in ("__init__.py", "plugin.yaml"):
                (plugin / name).write_text(name)
            runtime = OfflineRuntime(Path(root).resolve(), {})
            captured = {}

            async def request(method, params, *, timeout):
                captured.update(method=method, params=params, timeout=timeout)
                return {"endpoint": "http://127.0.0.1:18000", "token": "local"}

            runtime.request = request
            await runtime.launch_hermes({}, plugin, {})
            self.assertEqual(captured["method"], "hermes_start")
            self.assertEqual(captured["timeout"], 135)
            self.assertGreaterEqual(captured["timeout"], offline_worker.HERMES_START_TIMEOUT + 10)

    def test_reconnected_process_requires_positive_death_evidence(self):
        zombie = "123 (hermes gateway) Z " + " ".join(str(value) for value in range(1, 22))
        live = "123 (hermes gateway) S " + " ".join(str(value) for value in range(1, 22))
        with patch("maslow_voice.coordinator.Path.read_text", return_value=zombie):
            self.assertTrue(process_confirmed_dead(123, "19"))
        with patch("maslow_voice.coordinator.Path.read_text", return_value=live):
            self.assertFalse(process_confirmed_dead(123, "19"))
        with patch("maslow_voice.coordinator.Path.read_text", side_effect=FileNotFoundError):
            self.assertTrue(process_confirmed_dead(123, "19"))
        with patch("maslow_voice.coordinator.Path.read_text", side_effect=PermissionError):
            self.assertFalse(process_confirmed_dead(123, "19"))

    async def test_ensure_evicts_only_confirmed_dead_cached_client(self):
        class CachedClient:
            def __init__(self, dead):
                self.dead = dead

            def discard_dead_process(self):
                return self.dead

        with tempfile.TemporaryDirectory() as root:
            model = {"provider": "custom", "default": "fixture"}
            task = {"mode": "server", "project": root}
            key = hashlib.sha256(json.dumps([task["mode"], task["project"], model], sort_keys=True).encode()).hexdigest()[:24]
            runtime = HermesRuntime(Path(root).resolve(), SimpleNamespace(value={}), None, Path(root) / "tools.sock", "token")
            runtime.model_config = AsyncMock(return_value=(model, {}))

            alive = CachedClient(False)
            runtime.clients[key] = alive
            self.assertIs(await runtime.ensure(task), alive)

            runtime.clients[key] = CachedClient(True)
            runtime.processes[key] = object()
            with patch("maslow_voice.coordinator.shutil.which", return_value=None):
                with self.assertRaises(VoiceError) as failure:
                    await runtime.ensure(task)
            self.assertEqual(failure.exception.code, "HERMES_MISSING")
            self.assertNotIn(key, runtime.clients)
            self.assertNotIn(key, runtime.processes)


if __name__ == "__main__":
    unittest.main()
