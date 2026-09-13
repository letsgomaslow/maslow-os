import asyncio
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch
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

    async def test_confirmed_coordinator_exit_interrupts_without_resubmit_and_continue_starts_fresh(self):
        class Executor:
            def __init__(self, *, dead=False, result=""):
                self.dead, self.result = dead, result
                self.submits, self.discarded, self.submitted_attempt = 0, False, None

            def confirmed_process_exit(self):
                return self.dead

            def discard_dead_process(self):
                if not self.dead:
                    return False
                self.discarded = True
                return True

            async def submit(self, task):
                self.submits += 1
                self.submitted_attempt = task["attempt"]
                return {"run_id": "fresh-run"}

            async def status(self, run_id):
                if self.dead:
                    raise VoiceError("HTTP_FAILED", "coordinator unavailable")
                return {"status": "completed", "run_id": run_id, "output": self.result}

            async def events(self, run_id):
                if False:
                    yield {}

        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("dead-coordinator", BRIEF, root, "openai", "Fix navigation")
            store.update(task["id"], state="accepted", run_id="accepted-run")
            dead, fresh, children = Executor(dead=True), Executor(result="Recovered result"), AsyncMock()
            clients = iter((dead, fresh))

            async def factory(task):
                return next(clients)

            manager = TaskManager(store, factory, AsyncMock(), children)
            await manager._run(task["id"])
            interrupted = store.get(task["id"])
            self.assertEqual(interrupted["state"], "interrupted")
            self.assertEqual(interrupted["run_id"], "accepted-run")
            self.assertEqual(interrupted["error"]["code"], "COORDINATOR_EXITED")
            self.assertEqual(dead.submits, 0)
            children.cancel.assert_awaited_once_with(task["id"])

            await manager.action(task["id"], "continue", "Try again after the coordinator stopped")
            await asyncio.gather(*list(manager.monitors.values()))
            completed = store.get(task["id"])
            self.assertTrue(dead.discarded)
            self.assertEqual(fresh.submits, 1)
            self.assertEqual(fresh.submitted_attempt, 1)
            self.assertEqual(completed["state"], "completed")
            self.assertEqual(completed["result"], "Recovered result")
            await manager.close()
            store.close()

    async def test_transient_status_failure_keeps_reconnecting_without_resubmit(self):
        class Executor:
            def __init__(self):
                self.polls, self.submits = 0, 0

            def confirmed_process_exit(self):
                return False

            async def submit(self, task):
                self.submits += 1
                return {"run_id": "unexpected"}

            async def status(self, run_id):
                self.polls += 1
                if self.polls == 1:
                    raise VoiceError("HTTP_FAILED", "temporary failure")
                return {"status": "completed", "run_id": run_id, "output": "Eventually complete"}

            async def events(self, run_id):
                if False:
                    yield {}

        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("transient-coordinator", BRIEF, root, "openai", "Fix navigation")
            store.update(task["id"], state="running", run_id="known-run")
            executor = Executor()
            manager = TaskManager(store, AsyncMock(return_value=executor), AsyncMock())
            with patch("maslow_voice.tasks.asyncio.sleep", new=AsyncMock()):
                await manager._run(task["id"])
            completed = store.get(task["id"])
            self.assertEqual(executor.polls, 2)
            self.assertEqual(executor.submits, 0)
            self.assertEqual(completed["state"], "completed")
            self.assertEqual(completed["result"], "Eventually complete")
            await manager.close()
            store.close()

    async def test_explicit_dead_offline_worker_interrupts_without_resubmit(self):
        class OfflineExecutor:
            submits = 0

            async def submit(self, task):
                self.submits += 1
                return {"run_id": "unexpected"}

            async def status(self, run_id):
                raise VoiceError("OFFLINE_UNAVAILABLE", "offline worker exited")

            async def events(self, run_id):
                if False:
                    yield {}

        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("dead-offline-worker", BRIEF, root, "offline", "Fix navigation")
            store.update(task["id"], state="running", run_id="offline-run")
            executor, children = OfflineExecutor(), AsyncMock()
            manager = TaskManager(store, AsyncMock(return_value=executor), AsyncMock(), children)
            await manager._run(task["id"])
            interrupted = store.get(task["id"])
            self.assertEqual(interrupted["state"], "interrupted")
            self.assertEqual(interrupted["run_id"], "offline-run")
            self.assertEqual(interrupted["error"]["code"], "COORDINATOR_EXITED")
            self.assertEqual(executor.submits, 0)
            children.cancel.assert_awaited_once_with(task["id"])
            await manager.close()
            store.close()

    async def test_explicit_dead_offline_hermes_child_interrupts_without_resubmit(self):
        executor, children = AsyncMock(), AsyncMock()
        executor.record_process_exit = Mock()
        executor.status.side_effect = VoiceError("OFFLINE_HERMES_EXITED", "owned Hermes child exited")
        executor.confirmed_process_exit.return_value = False
        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("dead-offline-hermes", BRIEF, root, "offline", "Fix navigation")
            store.update(task["id"], state="running", run_id="offline-run")
            manager = TaskManager(store, AsyncMock(return_value=executor), AsyncMock(), children)
            await manager._run(task["id"])
            interrupted = store.get(task["id"])
            self.assertEqual(interrupted["state"], "interrupted")
            self.assertEqual(interrupted["run_id"], "offline-run")
            self.assertEqual(interrupted["error"]["code"], "COORDINATOR_EXITED")
            executor.submit.assert_not_awaited()
            executor.record_process_exit.assert_called_once_with()
            children.cancel.assert_awaited_once_with(task["id"])
            await manager.close()
            store.close()

    async def test_continue_queued_while_interrupted_monitor_drains_starts_after_cleanup(self):
        class DeadExecutor:
            def __init__(self):
                self.events_started = asyncio.Event()
                self.draining = asyncio.Event()
                self.release = asyncio.Event()

            def confirmed_process_exit(self):
                return True

            def discard_dead_process(self):
                return True

            async def status(self, run_id):
                await self.events_started.wait()
                raise VoiceError("HTTP_FAILED", "coordinator exited")

            async def events(self, run_id):
                self.events_started.set()
                try:
                    await asyncio.Event().wait()
                    yield {}
                finally:
                    self.draining.set()
                    await self.release.wait()

        class FreshExecutor:
            async def submit(self, task):
                return {"run_id": "continued-run"}

            async def status(self, run_id):
                return {"status": "completed", "run_id": run_id, "output": "Continued"}

            async def events(self, run_id):
                if False:
                    yield {}

        with tempfile.TemporaryDirectory() as root:
            store = TaskStore(root)
            task, _ = store.create("continue-during-cleanup", BRIEF, root, "openai", "Fix navigation")
            task = store.update(task["id"], state="accepted", run_id="dead-run")
            dead, fresh = DeadExecutor(), FreshExecutor()
            clients = iter((dead, fresh))

            async def factory(task):
                return next(clients)

            manager = TaskManager(store, factory, AsyncMock(), AsyncMock())
            manager._start(task)
            await dead.draining.wait()
            self.assertEqual(store.get(task["id"])["state"], "interrupted")
            await manager.action(task["id"], "continue", "Continue after cleanup")
            self.assertEqual(store.get(task["id"])["state"], "queued")
            self.assertFalse(manager.monitors[task["id"]].done())
            dead.release.set()
            for _ in range(20):
                await asyncio.sleep(0)
                if store.get(task["id"])["state"] == "completed":
                    break
            self.assertEqual(store.get(task["id"])["state"], "completed")
            self.assertEqual(store.get(task["id"])["result"], "Continued")
            await manager.close()
            store.close()
