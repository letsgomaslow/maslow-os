import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.workspaces import WorkspaceResolver
from test_service import FakeProvider

BRIEF = dict(objective="Task tracker", summary="Make a tracker", constraints=[], requested_output="index.html", tool_preference="codex", unresolved_questions=[])


class MvpServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.service = VoiceService(self.root / "state", self.root / "runtime", provider_factory=FakeProvider, credentials=AsyncMock())
        self.service.workspaces = WorkspaceResolver(self.root / "state", self.service.store, self.root / "projects")
        self.service.tasks._start = lambda task: None
        await self.service.start_voice(audio=False)
        self.service.desktop = AsyncMock()
        self.service.desktop.open.return_value = {"status": "opened", "verification": "window_observed"}
        await self.turn("first", "Create a tracker")

    async def asyncTearDown(self):
        await self.service.end_voice()
        for task in tuple(self.service.work):
            task.cancel()
        await asyncio.gather(*self.service.work, return_exceptions=True)
        self.service.store.close()
        self.temp.cleanup()

    async def turn(self, identity, words):
        await self.service.provider_event({"type": "transcript", "role": "user", "text": words, "turn_id": identity, "final": True})

    async def test_desktop_and_status_do_not_allocate_project(self):
        action = {"operation": "desktop", "application": "codex"}
        await self.service.conversation_action(action, "first")
        await self.service.conversation_action(action, "first")
        self.service.desktop.open.assert_awaited_once_with("codex")
        self.assertFalse((self.root / "projects").exists())
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "task", "action": "status"}, "first")
        self.assertEqual(self.service.store.list(), [])

    async def test_workspace_auto_dedup_and_view_request(self):
        result = await self.service.conversation_action(BRIEF, "first")
        duplicate = await self.service.conversation_action(dict(BRIEF, summary="Paraphrased"), "first")
        self.assertEqual(result["id"], duplicate["id"])
        self.assertTrue(Path(result["project"]).is_dir())
        self.assertEqual(self.service.snapshot()["task_view_request"]["task_id"], result["id"])
        self.assertEqual(len(self.service.store.list()), 1)
        self.assertEqual(self.service.project, result["project"])

    async def test_correction_targets_same_job_and_end_does_not_cancel(self):
        result = await self.service.conversation_action(BRIEF, "first")
        task = self.service.store.get(result["id"])
        self.service.tasks.action = AsyncMock(return_value=task)
        await self.turn("second", "Use three columns")
        await self.service.conversation_action({"operation": "task", "action": "steer", "text": "Use three columns"}, "second")
        self.service.tasks.action.assert_awaited_once_with(task["id"], "steer", "Use three columns")
        await self.service.end_voice()
        self.assertEqual(self.service.store.get(task["id"])["state"], "queued")
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "task", "action": "cancel"}, "second")
        self.assertEqual(self.service.tasks.action.await_count, 1)

    async def test_busy_codex_does_not_allocate_extra_folder(self):
        result = await self.service.conversation_action(BRIEF, "first")
        self.service.store.update(result["id"], selected_agent="codex")
        await self.turn("second", "Build another new project")
        with self.assertRaisesRegex(VoiceError, "current Codex job"):
            await self.service.conversation_action({"operation": "submit", "brief": BRIEF, "new_project": True}, "second")
        self.assertEqual(len(list((self.root / "projects").iterdir())), 1)

    async def test_model_cannot_supply_task_identity_or_approve(self):
        result = await self.service.conversation_action(BRIEF, "first")
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "task", "action": "cancel", "task_id": result["id"]}, "first")
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "task", "action": "approve"}, "first")

    async def test_only_one_checked_artifact_opens_for_show_result(self):
        result = await self.service.conversation_action(BRIEF, "first")
        self.service.store.update(result["id"], state="completed", artifacts=[{"path": "index.html", "exists": True}])
        await self.turn("second", "Show the result")
        await self.service.conversation_action({"operation": "task", "action": "show_result"}, "second")
        self.assertEqual(self.service.desktop.open_path.await_args.args[1], "index.html")

    async def test_completion_notice_waits_and_only_speaks_once(self):
        result = await self.service.conversation_action(BRIEF, "first")
        provider = self.service.provider
        provider.notify_task = AsyncMock(side_effect=[False, True])
        self.service.store.update(result["id"], state="completed", result="Created index.html")
        self.service.watch_gemini_task(result["id"])
        for _ in range(30):
            if not self.service.task_relays:
                break
            await asyncio.sleep(0.05)
        self.assertEqual(provider.notify_task.await_count, 2)
        self.assertFalse(self.service.task_relays)
        self.assertEqual(len(self.service.store.list()), 1)

    async def test_ended_session_never_receives_completion_notice(self):
        result = await self.service.conversation_action(BRIEF, "first")
        provider = self.service.provider
        provider.notify_task = AsyncMock(return_value=True)
        self.service.watch_gemini_task(result["id"])
        await self.service.end_voice()
        self.service.store.update(result["id"], state="completed")
        await asyncio.sleep(0.45)
        provider.notify_task.assert_not_awaited()

    async def test_ui_selection_sets_authoritative_spoken_target(self):
        result = await self.service.conversation_action(BRIEF, "first")
        await self.service.dispatch({"action": "task_action", "id": result["id"], "operation": "select"})
        self.assertEqual(self.service.current_task_id, result["id"])

    async def test_old_completion_notice_expires_without_speech(self):
        result = await self.service.conversation_action(BRIEF, "first")
        provider = self.service.provider
        provider.notify_task = AsyncMock(return_value=False)
        self.service.store.update(result["id"], state="completed")
        with patch("maslow_voice.daemon.TASK_NOTICE_SECONDS", 0):
            self.service.watch_gemini_task(result["id"])
            await asyncio.sleep(0.01)
        provider.notify_task.assert_not_awaited()
        self.assertFalse(self.service.task_relays)
