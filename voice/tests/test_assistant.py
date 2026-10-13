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

    async def test_private_material_and_derived_results_are_withheld_from_speech_summary(self):
        (self.workspace / "private.md").write_text("private selected bytes")
        task = await self.create({"documents": ["private.md"]})
        task = self.store.update(task["id"], title="private title", result="private derived result",
            activity=[{"text": "private activity"}], error={"code": "PRIVATE_ERROR", "message": "private error"},
            artifacts=[{"path": "private file"}])
        summary = VoiceService.task_summary(task)
        self.assertNotIn("private title", str(summary))
        self.assertNotIn("private derived result", str(summary))
        self.assertNotIn("private activity", str(summary))
        self.assertNotIn("private error", str(summary))
        self.assertNotIn("private file", str(summary))
        self.assertNotIn(str(self.workspace), str(summary))
        self.assertEqual(summary["id"], task["id"])
        self.assertEqual(summary["state"], task["state"])
        self.assertEqual(self.store.get(task["id"])["result"], "private derived result")

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

    async def test_running_managed_quota_parks_task_and_releases_process_without_resubmit(self):
        from maslow_voice.assistant_runtime import AssistantClient
        process = Mock(returncode=None)
        router = Mock(cooldown_message=Mock(return_value="Use Continue after the cooldown."), release=AsyncMock())
        client = AssistantClient("http://127.0.0.1:18574", "fixture-token", process, router, "fixture-owner")
        client.request = AsyncMock(side_effect=[{"run_id": "managed"}, {"status": "running"}])
        self.manager.assistant_factory = AsyncMock(return_value=client)
        with patch("maslow_voice.assistant_runtime._terminate_hermes_process_group", new_callable=AsyncMock) as terminate:
            task = await self.manager.submit_assistant("running-quota", "Save a note", str(self.workspace), {"note": "new.md"})
            await asyncio.gather(*list(self.manager.monitors.values()))
        saved = self.store.get(task["id"])
        self.assertEqual(saved["state"], "waiting_input")
        self.assertEqual(saved["error"]["code"], "FREE_AI_QUOTA_PAUSED")
        self.assertEqual(saved["granted_capabilities"], task["granted_capabilities"])
        self.assertEqual(saved["attempt"], task["attempt"])
        self.assertEqual(client.request.await_count, 2, "one submit and one status; no automatic resubmit")
        terminate.assert_awaited_once_with(process)
        router.release.assert_awaited_once_with("fixture-owner")
        self.assertTrue(client.released)
        self.assertFalse(self.manager.assistant_reservations)
        self.assertFalse((self.workspace / "new.md").exists())

    async def test_stop_during_held_status_preserves_intent_and_finishes_after_owned_cleanup(self):
        from maslow_voice.assistant_runtime import AssistantClient
        for hold_stop, terminal_during_cleanup, continue_before_stop_reply in ((False, False, False), (True, False, False), (False, True, False), (True, False, True)):
            with self.subTest(hold_stop=hold_stop, terminal_during_cleanup=terminal_during_cleanup, continue_before_stop_reply=continue_before_stop_reply):
                status_started, status_reply = asyncio.Event(), asyncio.Event()
                stop_started, stop_reply = asyncio.Event(), asyncio.Event()
                cleanup_started, cleanup_done = asyncio.Event(), asyncio.Event()
                if not hold_stop:
                    stop_reply.set()
                process = Mock(returncode=None)
                router = Mock(cooldown_message=Mock(return_value="Use Continue after the cooldown."), release=AsyncMock())
                client = AssistantClient("http://127.0.0.1:18574", "fixture-token", process, router, "fixture-owner")

                async def request(url, method="GET", *args, **kwargs):
                    if method == "POST" and url.endswith("/v1/runs"):
                        return {"run_id": "managed"}
                    if method == "POST" and url.endswith("/stop"):
                        stop_started.set()
                        await stop_reply.wait()
                        return {"status": "stopping"}
                    self.assertEqual(method, "GET")
                    status_started.set()
                    await status_reply.wait()
                    return {"status": "running"}

                async def terminate(owned):
                    self.assertIs(owned, process)
                    cleanup_started.set()
                    await cleanup_done.wait()
                    process.returncode = 0

                client.request = AsyncMock(side_effect=request)
                self.manager.assistant_factory = AsyncMock(return_value=client)
                stop = None
                with patch("maslow_voice.assistant_runtime._terminate_hermes_process_group", side_effect=terminate) as terminate_owned:
                    try:
                        task = await self.manager.submit_assistant("stop-quota-" + str(hold_stop) + str(terminal_during_cleanup) + str(continue_before_stop_reply), "Save a note", str(self.workspace), {"note": "new.md"})
                        await asyncio.wait_for(status_started.wait(), 2)
                        stop = asyncio.create_task(self.manager.action(task["id"], "cancel"))
                        await asyncio.wait_for(stop_started.wait(), 2)
                        if not hold_stop:
                            self.assertEqual((await stop)["state"], "stopping")
                        status_reply.set()
                        await asyncio.wait_for(cleanup_started.wait(), 2)
                        self.assertEqual(self.store.get(task["id"])["state"], "stopping", "Stop remains pending until owned cleanup finishes")
                        self.assertIsNone(self.store.get(task["id"])["error"])
                        expected_error = {"code": "LOCAL_CANCELLED", "message": "Stopped."} if terminal_during_cleanup else None
                        if terminal_during_cleanup:
                            self.store.update(task["id"], state="cancelled", error=expected_error)
                        cleanup_done.set()
                        await asyncio.gather(*list(self.manager.monitors.values()))
                        self.assertEqual(self.store.get(task["id"])["state"], "cancelled")
                        if continue_before_stop_reply:
                            with patch.object(self.manager, "_start") as start:
                                continued = await self.manager.action(task["id"], "continue", "Continue after the cooldown.")
                            start.assert_called_once_with(continued)
                            self.assertEqual(continued["attempt"], task["attempt"] + 1)
                        stop_reply.set()
                        if hold_stop:
                            stopped = await stop
                            if continue_before_stop_reply:
                                self.assertEqual(stopped, continued, "old Stop response cannot mutate a newer attempt")
                            else:
                                self.assertEqual(stopped["state"], "cancelled", "a late Stop response cannot resurrect stopping")
                    finally:
                        status_reply.set()
                        stop_reply.set()
                        cleanup_done.set()
                        if stop:
                            await asyncio.gather(stop, return_exceptions=True)
                        await asyncio.gather(*list(self.manager.monitors.values()))
                saved = self.store.get(task["id"])
                self.assertEqual(saved["state"], "queued" if continue_before_stop_reply else "cancelled")
                self.assertEqual(saved["error"], expected_error, "owned cleanup preserves any newer terminal outcome")
                self.assertEqual(saved["granted_capabilities"], task["granted_capabilities"])
                self.assertEqual(saved["attempt"], task["attempt"] + int(continue_before_stop_reply))
                self.assertEqual(client.request.await_count, 3, "one submit, one status and one Stop")
                terminate_owned.assert_awaited_once_with(process)
                router.release.assert_awaited_once_with("fixture-owner")
                self.assertTrue(client.released)
                self.assertEqual(process.returncode, 0)
                self.assertFalse(self.manager.assistant_reservations)
                if not continue_before_stop_reply:
                    self.assertFalse(self.store.active())
                self.assertNotIn("waiting_input", [event["data"].get("state") for event in self.store.events(task["id"])])
                self.assertFalse((self.workspace / "new.md").exists())

    async def test_old_quota_cleanup_cannot_cancel_or_revoke_a_newer_execution_session(self):
        from maslow_voice.assistant_runtime import AssistantClient
        status_started, status_reply = asyncio.Event(), asyncio.Event()
        cleanup_started, cleanup_done = asyncio.Event(), asyncio.Event()
        process = Mock(returncode=None)
        router = Mock(cooldown_message=Mock(return_value="Use Continue after the cooldown."), release=AsyncMock())
        client = AssistantClient("http://127.0.0.1:18574", "fixture-token", process, router, "fixture-owner")

        async def request(url, method="GET", *args, **kwargs):
            if method == "POST":
                return {"status": "stopping"} if url.endswith("/stop") else {"run_id": "managed"}
            status_started.set()
            await status_reply.wait()
            return {"status": "running"}

        async def terminate(owned):
            cleanup_started.set()
            await cleanup_done.wait()
            process.returncode = 0

        client.request = AsyncMock(side_effect=request)
        self.manager.assistant_factory = AsyncMock(return_value=client)
        self.manager.account_bridge = Mock(revoke=AsyncMock())
        worker = None
        newer_client = Mock(release=AsyncMock())
        with patch("maslow_voice.assistant_runtime._terminate_hermes_process_group", side_effect=terminate) as terminate_owned:
            try:
                task = await self.manager.submit_assistant("old-cleanup-new-session", "Save a note", str(self.workspace), {"note": "new.md"})
                worker = self.manager.monitors[task["id"]]
                await asyncio.wait_for(status_started.wait(), 2)
                await self.manager.action(task["id"], "cancel")
                status_reply.set()
                await asyncio.wait_for(cleanup_started.wait(), 2)
                self.store.update(task["id"], state="cancelled")
                with patch.object(self.manager, "_start"):
                    continued = await self.manager.action(task["id"], "continue", "Continue after the cooldown.")
                self.assertEqual(continued["attempt"], task["attempt"] + 1)
                expected = self.store.update(task["id"], state="stopping", run_id="new-run", session_id="new-session",
                    connect_session={"sessionId": "new-account-grant"})
                self.manager.clients[task["id"]] = newer_client
                cleanup_done.set()
                await worker
            finally:
                status_reply.set()
                cleanup_done.set()
                if worker:
                    await asyncio.gather(worker, return_exceptions=True)
        self.assertEqual(self.store.get(task["id"]), expected)
        self.assertEqual(expected["granted_capabilities"], task["granted_capabilities"])
        self.manager.account_bridge.revoke.assert_not_awaited()
        newer_client.release.assert_not_awaited()
        terminate_owned.assert_awaited_once_with(process)
        router.release.assert_awaited_once_with("fixture-owner")
        self.assertIn(task["id"], self.manager.assistant_reservations, "old cleanup cannot clear a newer client's reservation")

    async def test_late_account_revoke_failure_cannot_mark_a_newer_session(self):
        revoke_started, revoke_reply = asyncio.Event(), asyncio.Event()

        async def revoke(task):
            revoke_started.set()
            await revoke_reply.wait()
            raise VoiceError("FIXTURE_REVOKE_FAILED", "Fixture failure.")

        self.manager.account_bridge = Mock(revoke=AsyncMock(side_effect=revoke))
        task = await self.create({})
        old = self.store.update(task["id"], state="stopping", run_id="old-run", session_id="old-session",
            connect_session={"sessionId": "old-account-grant"})
        worker = asyncio.create_task(self.manager._revoke_finished_accounts(old))
        try:
            await asyncio.wait_for(revoke_started.wait(), 2)
            expected = self.store.update(task["id"], state="stopping", attempt=old["attempt"] + 1,
                run_id="new-run", session_id="new-session")
        finally:
            revoke_reply.set()
            await worker
        self.assertEqual(self.store.get(task["id"]), expected)
        self.manager.account_bridge.revoke.assert_awaited_once_with(old)
        self.assertFalse(self.store.get(task["id"]).get("account_cleanup_needed", False))

    async def test_stop_with_failed_owned_cleanup_does_not_claim_cancellation(self):
        from maslow_voice.assistant_runtime import AssistantClient
        status_started, status_reply = asyncio.Event(), asyncio.Event()
        process = Mock(returncode=None)
        router = Mock(cooldown_message=Mock(return_value="Use Continue after the cooldown."), release=AsyncMock())
        client = AssistantClient("http://127.0.0.1:18574", "fixture-token", process, router, "fixture-owner")

        async def request(url, method="GET", *args, **kwargs):
            if method == "POST":
                return {"status": "stopping"} if url.endswith("/stop") else {"run_id": "managed"}
            status_started.set()
            await status_reply.wait()
            return {"status": "running"}

        client.request = AsyncMock(side_effect=request)
        self.manager.assistant_factory = AsyncMock(return_value=client)
        worker = None
        with patch("maslow_voice.assistant_runtime._terminate_hermes_process_group", new_callable=AsyncMock, side_effect=RuntimeError("fixture cleanup failure")) as terminate:
            try:
                task = await self.manager.submit_assistant("stop-quota-cleanup-failure", "Save a note", str(self.workspace), {"note": "new.md"})
                worker = self.manager.monitors[task["id"]]
                await asyncio.wait_for(status_started.wait(), 2)
                self.assertEqual((await self.manager.action(task["id"], "cancel"))["state"], "stopping")
                status_reply.set()
                with self.assertRaisesRegex(RuntimeError, "fixture cleanup failure"):
                    await worker
            finally:
                status_reply.set()
                if worker:
                    await asyncio.gather(worker, return_exceptions=True)
        saved = self.store.get(task["id"])
        self.assertEqual(saved["state"], "stopping")
        self.assertIsNone(saved["error"])
        self.assertEqual(saved["granted_capabilities"], task["granted_capabilities"])
        self.assertEqual(saved["attempt"], task["attempt"])
        self.assertIsNone(process.returncode)
        self.assertIn(task["id"], self.manager.assistant_reservations)
        self.assertEqual(client.request.await_count, 3)
        terminate.assert_awaited_once_with(process)
        router.release.assert_awaited_once_with("fixture-owner")
        self.assertFalse({"cancelled", "waiting_input"} & {event["data"].get("state") for event in self.store.events(task["id"])})

    async def test_quota_response_cannot_overwrite_a_current_terminal_task(self):
        from maslow_voice.assistant_runtime import AssistantClient
        status_started, status_reply = asyncio.Event(), asyncio.Event()
        router = Mock(cooldown_message=Mock(return_value="Use Continue after the cooldown."), release=AsyncMock())
        client = AssistantClient("http://127.0.0.1:18574", "fixture-token", Mock(returncode=None), router, "fixture-owner")

        async def request(url, method="GET", *args, **kwargs):
            if method == "POST":
                return {"run_id": "managed"}
            status_started.set()
            await status_reply.wait()
            return {"status": "running"}

        client.request = AsyncMock(side_effect=request)
        self.manager.assistant_factory = AsyncMock(return_value=client)
        with patch("maslow_voice.assistant_runtime._terminate_hermes_process_group", new_callable=AsyncMock):
            try:
                task = await self.manager.submit_assistant("terminal-quota", "Draft text", str(self.workspace), {})
                await asyncio.wait_for(status_started.wait(), 2)
                expected = self.store.update(task["id"], state="cancelled", error={"code": "LOCAL_CANCELLED", "message": "Stopped."})
            finally:
                status_reply.set()
                await asyncio.gather(*list(self.manager.monitors.values()))
        self.assertEqual(self.store.get(task["id"]), expected)
        router.release.assert_awaited_once_with("fixture-owner")
        self.assertTrue(client.released)

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
