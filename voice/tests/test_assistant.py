import asyncio
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from maslow_voice.assistant import MAX_DOCUMENT, MAX_NOTE, POLICY_REVISION, WorkspaceTools, grant_workspace
from maslow_voice.daemon import VoiceService
from maslow_voice.errors import VoiceError
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager


class AssistantTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = TaskStore(self.root / "state")
        self.manager = TaskManager(self.store, AsyncMock(), AsyncMock())

    async def asyncTearDown(self):
        await self.manager.close()
        self.store.close()
        self.temp.cleanup()

    async def create(self, capabilities=None, identity="request"):
        return await self.manager.submit_assistant(identity, "Draft a short note", str(self.workspace), capabilities or {}, policy="review")

    async def test_grants_request_and_policy_survive_restart_and_cannot_be_changed(self):
        (self.workspace / "selected.md").write_text("selected")
        task = await self.create({"documents": ["selected.md"], "note": "new.md"})
        self.assertEqual(task["policy_revision"], POLICY_REVISION)
        self.store.close()
        self.store = TaskStore(self.root / "state")
        self.manager.store = self.store
        replay = await self.create({"documents": ["selected.md"], "note": "new.md"})
        self.assertEqual(replay["id"], task["id"])
        for changes in ({"documents": []}, {"documents": ["selected.md"], "note": "other.md"}, {"accounts": ["invented"]}):
            with self.assertRaises(VoiceError) as caught:
                await self.create(changes)
            self.assertEqual(caught.exception.code, "REQUEST_CONFLICT")
        for field in ("execution_connection", "policy_revision", "granted_capabilities", "requested_capabilities", "source", "project"):
            with self.assertRaises(VoiceError):
                self.store.update(task["id"], **{field: "changed"})

    async def test_note_has_checked_receipt_and_replay_after_saved_file_is_idempotent(self):
        task = await self.create({"note": "new.md"})
        self.store.update(task["id"], state="running")
        tools = WorkspaceTools(self.store)
        receipt = await tools.handle(task, "create_note", {"path": "new.md", "content": "# Draft\n"})
        self.assertEqual(receipt, {"path": str(self.workspace / "new.md"), "size": 8, "sha256": hashlib.sha256(b"# Draft\n").hexdigest()})
        self.assertEqual(await tools.handle(task, "create_note", {"path": "new.md", "content": "# Draft\n"}), receipt)
        replay = await self.create({"note": "new.md"})
        self.assertEqual(replay["id"], task["id"])
        with self.assertRaises(VoiceError):
            await tools.handle(task, "create_note", {"path": "new.md", "content": "changed"})
        self.assertEqual((self.workspace / "new.md").read_text(), "# Draft\n")

    async def test_partial_crash_note_is_not_overwritten_and_other_target_is_denied(self):
        task = await self.create({"note": "new.md"})
        data = "finished"
        (self.workspace / "new.md").write_text("partial")
        self.store.update(task["id"], note_receipt={"path": "new.md", "sha256": hashlib.sha256(data.encode()).hexdigest(), "state": "reserved"})
        with self.assertRaises(VoiceError):
            await WorkspaceTools(self.store).handle(task, "create_note", {"path": "new.md", "content": data})
        self.assertEqual((self.workspace / "new.md").read_text(), "partial")
        with self.assertRaises(VoiceError):
            await WorkspaceTools(self.store).handle(task, "create_note", {"path": "other.md", "content": data})
        self.assertFalse((self.workspace / "other.md").exists())

    async def test_saving_requires_grant_and_existing_targets_are_not_overwritten(self):
        task = await self.create()
        with self.assertRaises(VoiceError) as caught:
            await WorkspaceTools(self.store).handle(task, "create_note", {"path": "new.md", "content": "text"})
        self.assertEqual(caught.exception.code, "SAVE_NOT_GRANTED")
        self.store.update(task["id"], state="completed")
        (self.workspace / "existing.md").write_text("keep")
        with self.assertRaises(VoiceError) as caught:
            await self.create({"note": "existing.md"}, "next")
        self.assertEqual(caught.exception.code, "NOTE_EXISTS")

    async def test_paths_links_binary_and_oversized_inputs_fail_closed(self):
        outside = self.root / "outside.txt"
        outside.write_text("private")
        (self.workspace / "link.txt").symlink_to(outside)
        os.link(outside, self.workspace / "hard.txt")
        (self.workspace / "huge.txt").write_bytes(b"x" * (MAX_DOCUMENT + 1))
        (self.workspace / "binary.txt").write_bytes(b"\xff\x00")
        for name in ("../outside.txt", str(outside), "link.txt", "hard.txt", "huge.txt", "binary.txt", "./x.md", "a//x.md", "file.json"):
            with self.subTest(name=name), self.assertRaises(VoiceError):
                grant_workspace(str(self.workspace), {"documents": [name]})
        with self.assertRaises(VoiceError):
            grant_workspace("relative-workspace", {})
        (self.root / "alias").symlink_to(self.workspace)
        with self.assertRaises(VoiceError):
            grant_workspace(str(self.root / "alias"), {})

    async def test_file_replacement_and_symlink_swap_cannot_expand_selection(self):
        selected = self.workspace / "selected.md"
        selected.write_text("initial")
        task = await self.create({"documents": ["selected.md"]})
        selected.rename(self.workspace / "old.md")
        selected.write_text("replacement")
        tools = WorkspaceTools(self.store)
        with self.assertRaises(VoiceError):
            await tools.handle(task, "read_document", {"path": "selected.md"})
        selected.unlink()
        selected.symlink_to(self.root / "outside.md")
        with self.assertRaises(VoiceError):
            await tools.handle(task, "read_document", {"path": "selected.md"})
        with self.assertRaises(VoiceError):
            await tools.handle(task, "read_document", {"path": "old.md"})
        self.assertEqual(await tools.handle(task, "list_documents", {}), {"documents": ["selected.md"]})

    async def test_note_size_and_unknown_tools_arguments_are_denied(self):
        task = await self.create({"note": "new.md"})
        for operation, params in (("terminal", {"command": "id"}), ("list_documents", {"all": True}),
            ("create_note", {"path": "new.md", "content": "x" * (MAX_NOTE + 1)}),
            ("create_note", {"path": "new.md", "content": "\x00"})):
            with self.subTest(operation=operation), self.assertRaises(VoiceError):
                await WorkspaceTools(self.store).handle(task, operation, params)
        self.assertFalse((self.workspace / "new.md").exists())

    async def test_accounts_and_second_active_request_are_unavailable(self):
        with self.assertRaises(VoiceError) as caught:
            await self.create({"accounts": ["calendar"]})
        self.assertEqual(caught.exception.code, "MANAGED_ACCOUNTS_UNAVAILABLE")
        first = await self.create()
        with self.assertRaises(VoiceError) as caught:
            await self.create({}, "next")
        self.assertEqual(caught.exception.code, "ASSISTANT_TASK_ACTIVE")
        self.store.update(first["id"], state="completed")
        await self.create({}, "next")
        with self.assertRaises(VoiceError):
            await self.manager.action(first["id"], "continue", "more")

    async def test_review_start_uses_managed_factory_without_consumer_readiness(self):
        task = await self.create()
        self.manager.agent_selector = AsyncMock(side_effect=AssertionError("consumer profiles must not be read"))
        self.manager._start = Mock()
        started = await self.manager.action(task["id"], "start")
        self.assertEqual(started["state"], "queued")
        self.assertEqual(started["execution_connection"], "free-cloud")
        self.manager.agent_selector.assert_not_called()
        self.manager._start.assert_called_once()

    async def test_terminal_result_reserves_admission_until_owned_cleanup_finishes(self):
        cleanup_started, finish_cleanup = asyncio.Event(), asyncio.Event()
        class Client:
            async def submit(self, task):
                return {"run_id": "managed"}
            async def status(self, run_id):
                return {"status": "completed", "output": "done"}
            async def events(self, run_id):
                if False:
                    yield {}
            async def release(self):
                cleanup_started.set()
                await finish_cleanup.wait()
        self.manager.assistant_factory = AsyncMock(return_value=Client())
        first = await self.manager.submit_assistant("first", "Draft one", str(self.workspace), {})
        await asyncio.wait_for(cleanup_started.wait(), 2)
        self.assertEqual(self.store.get(first["id"])["state"], "completed")
        second_workspace = self.root / "second"
        second_workspace.mkdir()
        with self.assertRaises(VoiceError) as caught:
            await self.manager.submit_assistant("second", "Draft two", str(second_workspace), {})
        self.assertEqual(caught.exception.code, "ASSISTANT_TASK_ACTIVE")
        self.assertIsNone(self.store.by_request("second"))
        finish_cleanup.set()
        await asyncio.gather(*list(self.manager.monitors.values()))
        await self.manager.submit_assistant("second", "Draft two", str(second_workspace), {}, policy="review")

    async def test_quota_pause_keeps_request_and_grants_available_for_continue(self):
        self.manager.assistant_factory = AsyncMock(side_effect=VoiceError("FREE_AI_QUOTA_PAUSED", "Use Continue after the cooldown."))
        task = await self.manager.submit_assistant("quota", "Draft a note", str(self.workspace), {"note": "new.md"})
        await asyncio.gather(*list(self.manager.monitors.values()))
        paused = self.store.get(task["id"])
        self.assertEqual(paused["state"], "waiting_input")
        self.assertEqual(paused["error"]["code"], "FREE_AI_QUOTA_PAUSED")
        self.assertEqual(paused["granted_capabilities"], task["granted_capabilities"])
        self.assertFalse(self.manager.assistant_reservations)
        cancelled = await self.manager.action(task["id"], "cancel")
        self.assertEqual(cancelled["state"], "cancelled")
        self.assertFalse(self.store.active())

    async def test_model_claim_cannot_complete_a_requested_note_without_checked_bytes(self):
        class Client:
            async def submit(self, task):
                return {"run_id": "claim"}
            async def status(self, run_id):
                return {"status": "completed", "output": "I saved the requested note."}
            async def events(self, run_id):
                if False:
                    yield {}
            async def release(self):
                pass
        self.manager.assistant_factory = AsyncMock(return_value=Client())
        task = await self.manager.submit_assistant("claim", "Save a note", str(self.workspace), {"note": "new.md"})
        await asyncio.gather(*list(self.manager.monitors.values()))
        saved = self.store.get(task["id"])
        self.assertEqual(saved["state"], "interrupted")
        self.assertEqual(saved["error"]["code"], "NOTE_NOT_CREATED")
        self.assertIn("saved", saved["result"], "The model's unverified report remains reviewable")
        self.assertFalse((self.workspace / "new.md").exists())

    async def test_restart_does_not_replay_managed_work_and_continue_keeps_grants(self):
        task = await self.create({"note": "new.md"})
        self.store.update(task["id"], state="running", run_id="old")
        await self.manager.recover()
        self.assertFalse(self.manager.monitors)
        self.assertEqual(self.store.get(task["id"])["state"], "interrupted")
        self.manager._start = Mock()
        result = await self.manager.action(task["id"], "continue", "Please finish")
        self.assertEqual(result["attempt"], 1)
        self.assertEqual(result["granted_capabilities"], task["granted_capabilities"])

    async def test_typed_submission_never_starts_audio_or_conversation_provider(self):
        provider = Mock(side_effect=AssertionError("conversation provider must not be created"))
        audio = Mock(side_effect=AssertionError("microphone must not be created"))
        service = VoiceService(self.root / "voice-state", self.root / "runtime", provider_factory=provider,
            audio_transport_factory=audio, credentials=Mock())
        service.settings.update({"task_policy": "review", "execution_connection": "free-cloud"})
        try:
            response = await service.dispatch({"action": "task_submit", "request_id": "typed-no-audio", "text": "Draft an invitation", "project": str(self.workspace), "capabilities": {}})
            self.assertEqual(response["submitted_request_id"], "typed-no-audio")
            self.assertEqual(service.store.get(response["task"]["id"])["execution_connection"], "free-cloud")
            self.assertFalse(service.voice["enabled"])
            provider.assert_not_called()
            audio.assert_not_called()
            await service.dispatch({"action": "configure", "settings": {"execution_connection": "existing"}})
            self.assertEqual(service.store.get(response["task"]["id"])["execution_connection"], "free-cloud")
        finally:
            await service.tasks.close()
            service.store.close()

    async def test_connection_probe_does_not_certify_fallback_as_the_requested_model(self):
        service = VoiceService(self.root / "voice-state", self.root / "runtime", credentials=Mock())
        response = {"model": "openai/gpt-oss-20b", "choices": [{"message": {"tool_calls": [{"function": {
            "name": "maslow_ready", "arguments": '{"value":"READY"}'}}]}}]}
        try:
            with patch("maslow_voice.http.request_json", AsyncMock(return_value=response)) as probe:
                with self.assertRaises(VoiceError) as caught:
                    await service.free_ai_probe({"endpoint": "http://127.0.0.1:18573/v1", "token": "synthetic"})
            self.assertEqual(caught.exception.code, "FREE_AI_ROUTE_SUBSTITUTED")
            self.assertEqual(probe.await_count, 1)
        finally:
            await service.tasks.close()
            service.store.close()
