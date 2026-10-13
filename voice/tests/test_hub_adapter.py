import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError


class HubAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.credentials = AsyncMock()
        self.credentials.get.return_value = "saved-private-key"
        self.ticket_root = patch("maslow_voice.free_ai_delivery.TICKET_ROOT", self.root / "tickets")
        self.ticket_root.start()
        self.addCleanup(self.ticket_root.stop)
        self.service = VoiceService(self.root / "state", self.root / "runtime", credentials=self.credentials)
        self.credentials.reset_mock()

    async def asyncTearDown(self):
        self.service.store.close()
        self.temporary.cleanup()

    async def test_cached_status_never_imports_router_probes_keys_or_audio(self):
        self.service.check_readiness = AsyncMock(side_effect=AssertionError("provider probe"))
        self.service.start_voice = AsyncMock(side_effect=AssertionError("audio startup"))
        self.service._free_ai = Mock(side_effect=AssertionError("router import"))
        self.service.delivery.closed = True
        task, _ = self.service.store.create("test-task", {"objective": "Fix API_KEY=private-key /private/project sk-privatekey", "summary": "private-request"}, str(self.root), "gemini_live", "private-source")
        self.service.store.update(task["id"], state="awaiting_approval", result="private-result", error={"message": "private-error"})
        self.service.settings.value["gemini_live_prompt"] = "private-prompt"
        self.service.settings.value["server_url"] = "https://private/secret-account"
        self.service.settings.value["model"] = "sk-privatekey"
        self.service.session["transcript"] = [{"text": "private-transcript"}]
        result = await self.service.dispatch({"action": "hub_status"})
        view = result["hub"]
        self.assertEqual(task["id"], view["tasks"][0]["handoff"]["taskId"])
        self.assertEqual("awaiting_approval", view["tasks"][0]["status"])
        self.assertFalse(view["canConfigure"])
        self.assertTrue(view["maintenance"])
        self.assertEqual("maintenance", view["state"])
        self.assertFalse(view["ready"])
        self.assertFalse(view["capabilities"]["taskOpen"])
        self.assertNotIn("server_url", view["settings"])
        self.assertIn("Puck", view["voices"]["gemini_live_voice"])
        self.assertIn("cedar", view["voices"]["realtime_voice"])
        encoded = json.dumps(result)
        for private in ("private-key", "/private/project", "sk-privatekey", "private-request", "private-source", "private-result", "private-error", "private-prompt", "private-transcript", "secret-account"):
            self.assertNotIn(private, encoded)
        self.assertEqual([], self.credentials.mock_calls)
        self.service.check_readiness.assert_not_called()
        self.service.start_voice.assert_not_called()
        self.service._free_ai.assert_not_called()

    async def test_history_bounded_and_dismissed_hidden(self):
        for number in range(55):
            self.service.store.create(str(number), {"objective": f"Task {number}", "summary": "private"}, str(self.root), "gemini_live", "private")
        latest = self.service.store.list(1)[0]
        self.service.store.update(latest["id"], dismissed=True)
        view = (await self.service.dispatch({"action": "hub_status"}))["hub"]
        self.assertLessEqual(len(view["tasks"]), 50)
        self.assertNotIn(latest["id"], [task["id"] for task in view["tasks"]])

    async def test_hub_configuration_blocks_active_session_and_tasks(self):
        self.service.voice["enabled"] = True
        with self.assertRaises(VoiceError) as caught:
            await self.service.dispatch({"action": "hub_configure", "request": {"action": "credential", "name": "google", "value": "private-value"}})
        self.assertEqual("SESSION_ACTIVE", caught.exception.code)
        self.service.voice["enabled"] = False
        self.service.store.create("active", {"objective": "Work", "summary": "Work"}, str(self.root), "gemini_live", "Work")
        with self.assertRaises(VoiceError) as caught:
            await self.service.dispatch({"action": "hub_configure", "request": {"action": "configure", "settings": {"mode": "gpt_live"}}})
        self.assertEqual("TASKS_ACTIVE", caught.exception.code)
        self.assertEqual([], self.credentials.mock_calls)

    async def test_blank_credential_retains_without_reading_or_writing_keyring(self):
        result = await self.service.dispatch({"action": "hub_configure", "request": {"action": "credential", "name": "google", "value": "  "}})
        self.assertEqual({"saved": True}, result)
        self.assertEqual([], self.credentials.mock_calls)

    async def test_reconnect_and_provider_cleanup_are_active_conversations(self):
        self.service.voice["enabled"] = False
        self.service.provider = None
        for field in ("reconnect_task", "provider_cleanup"):
            worker = Mock()
            worker.done.return_value = False
            setattr(self.service, field, worker)
            view = (await self.service.dispatch({"action": "hub_status"}))["hub"]
            self.assertTrue(view["sessionActive"])
            self.assertFalse(view["canConfigure"])
            with self.assertRaises(VoiceError) as caught:
                await self.service.dispatch({"action": "hub_configure", "request": {"action": "configure", "settings": {"mode": "gpt_live"}}})
            self.assertEqual("SESSION_ACTIVE", caught.exception.code)
            worker.cancel.assert_not_called()
            setattr(self.service, field, None)
        self.assertEqual([], self.credentials.mock_calls)

    async def test_background_work_blocks_configuration(self):
        cases = [("agent_jobs", {"web-1"}), ("jobs", {"job": {"state": "running"}}), ("action_work", {"action": 1})]
        for field, value in cases:
            original = getattr(self.service, field)
            setattr(self.service, field, value)
            view = (await self.service.dispatch({"action": "hub_status"}))["hub"]
            self.assertTrue(view["tasksActive"])
            self.assertFalse(view["canConfigure"])
            with self.assertRaises(VoiceError) as caught:
                await self.service.dispatch({"action": "hub_configure", "request": {"action": "credential", "name": "google", "value": "synthetic-key"}})
            self.assertEqual("TASKS_ACTIVE", caught.exception.code)
            setattr(self.service, field, original)
        self.assertEqual([], self.credentials.mock_calls)

    async def test_configuration_uses_existing_action_and_no_secret_in_response(self):
        self.service.check_readiness = AsyncMock(return_value={"ready": True})
        result = await self.service.dispatch({"action": "hub_configure", "request": {"action": "credential", "name": "google", "value": "test-private-key"}})
        self.credentials.set.assert_awaited_once_with("google", "test-private-key")
        self.assertEqual({"saved": True}, result)
        self.service.check_readiness.assert_awaited_once()

    async def test_settings_allowlist_rejects_unsupported_or_execution_actions(self):
        for request in ({"action": "task_submit", "text": "execute"}, {"action": "configure", "settings": {"gemini_live_prompt": "override"}}, {"action": "configure", "settings": {"gemini_live_voice": "not-a-supported-voice"}}, {"action": []}):
            with self.assertRaises(VoiceError):
                await self.service.dispatch({"action": "hub_configure", "request": request})

    async def test_exact_saved_task_selection_retains_existing_ui_request(self):
        first, _ = self.service.store.create("first", {"objective": "First", "summary": "First"}, str(self.root), "gemini_live", "First")
        second, _ = self.service.store.create("second", {"objective": "Second", "summary": "Second"}, str(self.root), "gemini_live", "Second")
        self.service.publish = AsyncMock()
        result = await self.service.dispatch({"action": "task_action", "task_id": first["id"], "operation": "select"})
        self.assertEqual({}, result)
        self.assertEqual(first["id"], self.service.task_view_request["task_id"])
        self.assertNotEqual(second["id"], self.service.task_view_request["task_id"])
        self.assertEqual(first["id"], self.service.current_task_id)
        self.service.publish.assert_awaited_once()

    async def test_configuration_blocks_concurrent_session_admission(self):
        entered, finish = asyncio.Event(), asyncio.Event()
        async def readiness(*args, **kwargs):
            entered.set()
            await finish.wait()
        self.service.check_readiness = readiness
        task = asyncio.create_task(self.service.dispatch({"action": "hub_configure", "request": {"action": "credential", "name": "google", "value": "private-key"}}))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            with self.assertRaises(VoiceError) as caught:
                await self.service.dispatch({"action": "start_voice"})
            self.assertEqual("SETTINGS_BUSY", caught.exception.code)
        finally:
            finish.set()
            await task
        self.assertFalse(self.service.hub_configuring)


if __name__ == "__main__":
    unittest.main()
