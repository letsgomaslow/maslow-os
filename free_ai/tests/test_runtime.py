import asyncio
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import time
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from maslow_free_ai.credentials import EncryptionKey
from maslow_free_ai.errors import FreeAIError
from maslow_free_ai.runtime import MODELS, RouterRuntime
from maslow_free_ai.state import State


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.keys = Mock()
        self.keys.get = AsyncMock(return_value="a" * 64)
        self.keys.create = AsyncMock()
        self.package = self.root / "package"
        (self.package / "node/bin").mkdir(parents=True)
        (self.package / "router/server/dist").mkdir(parents=True)
        (self.package / "maslow_free_ai").mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / "maslow_free_ai/router_worker.py", self.package / "maslow_free_ai/router_worker.py")
        (self.package / "router/server/dist/maslow-main.js").write_text("fixture only")
        # Real owned OS process and socket, synthetic local router. No inference.
        node = self.package / "node/bin/node"
        node.write_text('''#!/usr/bin/python
import hashlib, json, signal, socket, sys, time
p = json.loads(sys.stdin.read())
s = socket.socket(); s.bind(('127.0.0.1', p['port'])); s.listen()
print(json.dumps({'event':'ready','host':'127.0.0.1','port':p['port'],'tokenId':hashlib.sha256(p['instanceToken'].encode()).hexdigest()}), flush=True)
while True: time.sleep(1)
''')
        node.chmod(0o755)
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            self.port = candidate.getsockname()[1]
        self.runtime = RouterRuntime(self.root / "state", keys=self.keys, package=self.package, port=self.port, grace=0.01)
        self.runtime.task_supported = Mock(return_value=True)

    async def asyncTearDown(self):
        await self.runtime.close()
        self.temp.cleanup()

    async def test_failed_preparation_without_marker_preserves_admission_and_truthful_status(self):
        self.runtime.state.update(enabled=True, configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        with self.assertRaises(FreeAIError):
            await self.runtime.prepare_recovery({})
        self.assertTrue(self.runtime.admission)
        self.assertTrue(self.runtime.status()["ready"])
        with patch("maslow_free_ai.recovery.atomic_json", side_effect=OSError(28, "Full")):
            with self.assertRaises(OSError):
                await self.runtime.prepare_recovery({"maslow-free-ai":"1" * 64})
        self.assertFalse(self.runtime.recovery.pending())
        self.assertTrue(self.runtime.admission)
        self.assertTrue(self.runtime.status()["ready"])
        self.runtime.admission = False
        self.assertFalse(self.runtime.status()["ready"])
        self.assertEqual(self.runtime.status()["state"], "maintenance")

    async def test_recovery_closes_admission_survives_restart_and_requires_recheck(self):
        self.keys.get.return_value = None
        receipt = await self.runtime.prepare_recovery({"maslow-free-ai": "1" * 64})
        self.assertEqual(receipt["kind"], "fresh")
        self.assertEqual(self.runtime.status()["state"], "maintenance")
        restarted = RouterRuntime(self.runtime.state.directory, keys=self.keys, package=self.package, port=self.port)
        self.assertFalse(restarted.admission)
        with self.assertRaises(FreeAIError):
            await restarted.acquire("new-task")
        await restarted.abandon_recovery()
        self.assertFalse(restarted.status()["ready"])
        self.assertFalse(restarted.status()["enabled"])
        await restarted.close()

    async def test_recovery_rejects_owner_without_terminating_task(self):
        self.runtime.state.update(enabled=True, configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        await self.runtime.acquire("active-task")
        process = self.runtime.process
        with self.assertRaises(FreeAIError) as error:
            await self.runtime.prepare_recovery({"maslow-free-ai": "1" * 64})
        self.assertEqual(error.exception.code, "TASKS_ACTIVE")
        self.assertIsNone(process.returncode)
        self.assertFalse(self.runtime.recovery.pending())

    async def test_status_never_starts_router_or_reads_keyring(self):
        self.assertFalse(self.runtime.status()["ready"])
        self.assertIsNone(self.runtime.process)
        self.keys.get.assert_not_called()

    async def test_owned_process_lifetime_survives_disable_and_stops_after_last_release(self):
        self.runtime.state.update(enabled=True, configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        route = await self.runtime.acquire("task-1")
        process = self.runtime.process
        self.assertIn("token", route)
        self.assertNotIn("a" * 64, (self.runtime.state.path).read_text())
        await self.runtime.enable(False)
        self.assertIsNone(process.returncode, "changing a new-task choice must not terminate active work")
        with self.assertRaises(FreeAIError):
            await self.runtime.acquire("task-2")
        await self.runtime.release("task-1")
        await asyncio.sleep(0.06)
        self.assertIsNotNone(process.returncode)
        self.assertIsNone(self.runtime.process)

    async def test_occupied_port_is_safe_error_without_stopping_other_listener(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", self.port))
            listener.listen()
            with self.assertRaises(FreeAIError) as caught:
                await self.runtime._start()
            self.assertEqual(caught.exception.code, "FREE_AI_PORT_OCCUPIED")
            self.assertEqual(listener.getsockname()[1], self.port)
            self.assertIsNone(self.runtime.process)

    async def test_setup_persistence_failure_after_start_always_stops_router(self):
        self.runtime._start = AsyncMock(return_value={})
        self.runtime._stop = AsyncMock()
        self.runtime.state.update = Mock(side_effect=[None, OSError("disk full")])
        probe = AsyncMock()
        with self.assertRaises(OSError):
            await self.runtime.setup("gsk_" + "x" * 40, True, probe)
        self.assertEqual(self.runtime._stop.await_count, 2)
        probe.assert_not_called()

    async def test_failed_connection_test_clears_readiness_and_stops_router(self):
        self.runtime.state.update(configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        probe = AsyncMock(side_effect=FreeAIError("TEST_FAILED", "test failed"))
        with self.assertRaises(FreeAIError):
            await self.runtime.test(probe)
        self.assertEqual(self.runtime.state.value["verified_routes"], [])
        self.assertIsNone(self.runtime.process)
        self.assertFalse(self.runtime.status()["ready"])

    async def test_keyring_failure_and_lost_matching_key_never_generate_plaintext_fallback(self):
        self.keys.get.side_effect = FreeAIError("KEYRING_LOCKED", "locked")
        with self.assertRaises(FreeAIError):
            await self.runtime._start("gsk_" + "x" * 40)
        self.keys.create.assert_not_called()
        self.assertIsNone(self.runtime.process)
        self.keys.get.side_effect = None
        self.keys.get.return_value = None
        self.runtime.database.write_bytes(b"existing encrypted database")
        with self.assertRaises(FreeAIError) as caught:
            await self.runtime._start("gsk_" + "x" * 40)
        self.assertEqual(caught.exception.code, "ENCRYPTION_KEY_MISSING")
        self.keys.create.assert_not_called()

    async def test_cancelled_setup_probe_cleans_owned_process(self):
        started = asyncio.Event()
        async def probe(route):
            started.set()
            await asyncio.Event().wait()
        setup = asyncio.create_task(self.runtime.setup("gsk_" + "x" * 40, True, probe))
        await asyncio.wait_for(started.wait(), 3)
        process = self.runtime.process
        setup.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await setup
        self.assertIsNotNone(process.returncode)
        self.assertIsNone(self.runtime.process)

    async def test_shared_cooldown_blocks_new_work_without_starting_a_provider(self):
        self.runtime.state.update(enabled=True, configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        with closing(sqlite3.connect(self.runtime.database)) as db, db:
            db.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
            db.execute("INSERT INTO settings VALUES(?,?)", ("maslow_groq_cooldown_until", str(int((time.time() + 3600) * 1000))))
        self.runtime.database.chmod(0o600)
        with self.assertRaises(FreeAIError) as caught:
            await self.runtime.acquire("task")
        self.assertEqual(caught.exception.code, "FREE_AI_QUOTA_PAUSED")
        self.assertIn("Continue", caught.exception.message)
        self.assertIsNone(self.runtime.process)

    async def test_old_voice_cannot_be_advertised_as_task_ready(self):
        self.runtime.state.update(enabled=True, configured=True, free_plan="user-confirmed", verified_routes=list(MODELS))
        self.runtime.task_supported.return_value = False
        self.assertFalse(self.runtime.status()["ready"])


class CredentialTests(unittest.IsolatedAsyncioTestCase):
    async def test_locked_items_do_not_fall_through_to_lookup_or_creation(self):
        key = EncryptionKey()
        key._run = AsyncMock(return_value=(0, "(@ao [], [objectpath '/org/freedesktop/secrets/item/1'])"))
        with self.assertRaises(FreeAIError) as caught:
            await key.get()
        self.assertEqual(caught.exception.code, "KEYRING_LOCKED")
        self.assertEqual(key._run.await_count, 1)

    async def test_unavailable_service_is_never_interpreted_as_missing_key(self):
        key = EncryptionKey()
        key._run = AsyncMock(return_value=(1, ""))
        with self.assertRaises(FreeAIError):
            await key.create("a" * 64)
        self.assertEqual(key._run.await_count, 1)

    async def test_missing_key_creation_round_trips_over_stdin(self):
        key = EncryptionKey()
        key._run = AsyncMock(side_effect=[(0, "(@ao [], @ao [])"), (0, ""),
            (0, "([objectpath '/org/freedesktop/secrets/item/1'], @ao [])"), (0, "a" * 64)])
        await key.create("a" * 64)
        store = key._run.await_args_list[1]
        self.assertNotIn("a" * 64, store.args[0])
        self.assertEqual(store.args[1], "a" * 64)


class StateTests(unittest.TestCase):
    def test_state_permissions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            state = State(Path(root) / "state")
            state.update(enabled=True)
            self.assertEqual(state.directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual(state.path.stat().st_mode & 0o777, 0o600)
            alias = Path(root) / "alias"
            alias.symlink_to(state.directory)
            with self.assertRaises(FreeAIError):
                State(alias)
