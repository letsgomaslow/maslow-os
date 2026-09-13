import asyncio
import tempfile
import unittest
from unittest.mock import AsyncMock
from pathlib import Path

from maslow_voice.errors import VoiceError
from maslow_voice.hermes import HermesClient, normalized_status
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager, validate_brief

BRIEF = {"objective": "Fix navigation", "summary": "Fix the selected project's navigation.", "constraints": ["Preserve unrelated changes"], "requested_output": "A tested change", "tool_preference": "codex"}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = TaskStore(self.temp.name)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_repeated_request_recovers_identical_task_across_restart(self):
        task, created = self.store.create("request-1", BRIEF, "/project", "openai", "Fix navigation")
        self.assertTrue(created)
        self.store.update(task["id"], state="accepted", run_id="run_1")
        self.store.close()
        self.store = TaskStore(self.temp.name)
        replay, created = self.store.create("request-1", BRIEF, "/project", "openai", "Fix navigation")
        self.assertFalse(created)
        self.assertEqual(replay["id"], task["id"])
        self.assertEqual(replay["run_id"], "run_1")
        with self.assertRaises(VoiceError):
            self.store.create("request-1", BRIEF, "/other", "openai", "Fix navigation")

    def test_mode_is_immutable_and_history_contains_lifecycle(self):
        task, _ = self.store.create("1", BRIEF, "/project", "offline", "Fix navigation")
        with self.assertRaises(VoiceError):
            self.store.update(task["id"], mode="openai")
        self.store.update(task["id"], state="running")
        self.assertEqual([event["data"]["state"] for event in self.store.events(task["id"])], ["queued", "running"])

    def test_permissions_and_executable_fields_are_not_voice_brief_fields(self):
        for key in ("permissions", "command", "endpoint", "approval", "project"):
            with self.assertRaises(VoiceError):
                validate_brief(dict(BRIEF, **{key: "invented"}))
        self.assertEqual(validate_brief(BRIEF)["tool_preference"], "codex")


class HermesTests(unittest.IsolatedAsyncioTestCase):
    async def test_submission_uses_authoritative_context_and_idempotency(self):
        calls = []
        async def request(*args, **kwargs):
            calls.append((args, kwargs))
            return {"run_id": "run_1", "status": "started"}
        client = HermesClient("http://127.0.0.1:9000", "test-token", request=request)
        task = {"id": "task_1", "request_id": "source_1", "brief": BRIEF, "source": "Fix this navigation", "project": "/work", "mode": "offline"}
        await client.submit(task)
        self.assertEqual(calls[0][1]["headers"], {"Idempotency-Key": "source_1:0"})
        self.assertEqual(calls[0][0][2]["session_id"], "task_1")
        with self.assertRaises(VoiceError):
            await client.status("../../v1/admin")
        with self.assertRaises(VoiceError):
            HermesClient("https://user-server.invalid", "token")

    async def test_approval_is_exact_once_not_session_wide(self):
        calls = []
        async def request(*args, **kwargs):
            calls.append(args)
            return {}
        client = HermesClient("http://127.0.0.1:9000", "token", request=request)
        await client.approve("run_1", "approval_1", True)
        self.assertEqual(calls[0][2], {"choice": "once", "request_id": "approval_1"})

    async def test_reconnect_does_not_resubmit_known_run(self):
        class Executor:
            submits = 0
            polls = 0
            async def submit(self, task):
                self.submits += 1
                return {"run_id": "run_known"}
            async def status(self, run_id):
                self.polls += 1
                return {"status": "completed", "run_id": run_id, "output": "Actual result"}
            async def events(self, run_id):
                if False:
                    yield {}
        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("source_1", BRIEF, root, "openai", "Fix this")
            store.update(task["id"], state="running", run_id="run_known")
            executor = Executor()
            async def factory(task):
                return executor
            async def publish():
                pass
            manager = TaskManager(store, factory, publish)
            await manager.recover()
            await asyncio.gather(*list(manager.monitors.values()))
            self.assertEqual(executor.submits, 0)
            self.assertEqual(store.get(task["id"])["result"], "Actual result")
            await manager.close()
            store.close()

    async def test_interrupted_does_not_become_completed(self):
        result = normalized_status({"status": "interrupted", "output": "partial"})
        self.assertEqual(result["state"], "interrupted")
        self.assertEqual(result["result"], "partial")
        self.assertIsNotNone(result["error"])

    async def test_cancel_during_coordinator_start_never_submits(self):
        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            starting, release = asyncio.Event(), asyncio.Event()
            executor = AsyncMock()
            async def factory(task):
                starting.set()
                await release.wait()
                return executor
            manager = TaskManager(store, factory, AsyncMock())
            task = await manager.submit("cancel-before-handoff", BRIEF, root, "openai", "Fix navigation")
            await starting.wait()
            await manager.action(task["id"], "cancel")
            release.set()
            await asyncio.gather(*list(manager.monitors.values()))
            executor.submit.assert_not_awaited()
            self.assertEqual(store.get(task["id"])["state"], "cancelled")
            await manager.close()
            store.close()

    async def test_lost_parent_run_cancels_live_children(self):
        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("lost-run", BRIEF, root, "openai", "Fix navigation")
            store.update(task["id"], state="running", run_id="gone")
            executor, children = AsyncMock(), AsyncMock()
            executor.status.side_effect = VoiceError("NOT_FOUND", "Run lost")
            manager = TaskManager(store, AsyncMock(return_value=executor), AsyncMock(), children)
            await manager._run(task["id"])
            children.cancel.assert_awaited_once_with(task["id"])
            self.assertEqual(store.get(task["id"])["state"], "interrupted")
            await manager.close()
            store.close()
