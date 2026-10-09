import asyncio
import tempfile
import time
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
        self.service.desktop.open.assert_awaited_once_with("codex", None)
        self.assertFalse((self.root / "projects").exists())
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "task", "action": "status"}, "first")
        self.assertEqual(self.service.store.list(), [])

    async def test_website_is_forwarded_with_caption_published_first(self):
        seen = []
        async def open_app(application, url=None):
            seen.append((application, url, self.service.voice.get("action_caption")))
            return {"application": application, "status": "opened"}
        self.service.desktop.open.side_effect = open_app
        await self.service.conversation_action({"operation": "desktop", "application": "browser", "url": "https://www.github.com/x"}, "first")
        self.assertEqual(seen, [("browser", "https://www.github.com/x", "Opening github.com…")])
        with self.assertRaisesRegex(VoiceError, "unsupported fields"):
            await self.service.conversation_action({"operation": "desktop", "application": "browser", "text": "hi"}, "first")

    async def test_agent_words_are_captioned_once_and_retries_reuse_the_receipt(self):
        seen = []
        async def tell(agent, text, reply, *, title=None, busy_ok=True):
            seen.append((agent, text, reply, self.service.voice.get("action_caption"), busy_ok))
            return {"agent": agent, "status": "sent"}
        self.service.desktop.tell.side_effect = tell
        action = {"operation": "agent", "agent": "codex", "text": "add a dark mode toggle", "reply": ""}
        await self.service.conversation_action(action, "first")
        await self.service.conversation_action(action, "first")
        # A plain instruction never redirects work Codex is already doing.
        self.assertEqual(seen, [("codex", "add a dark mode toggle", "", "Telling Codex: add a dark mode toggle", False)])
        with self.assertRaisesRegex(VoiceError, "unsupported fields"):
            await self.service.conversation_action(action | {"application": "terminal"}, "first")

    async def test_waiting_agent_prompt_is_shown_not_answered(self):
        self.service.desktop.tell.return_value = {"agent": "codex", "status": "needs_answer", "prompt": "Would you like to run the following command?"}
        result = await self.service.conversation_action({"operation": "agent", "agent": "codex", "text": "hi", "reply": ""}, "first")
        self.assertEqual(result["status"], "needs_answer")
        self.assertEqual(self.service.voice["action_caption"], "Codex is waiting for your answer")
        self.assertEqual(self.service.action_caption({"operation": "agent", "agent": "codex", "reply": "approve"}), "Approving in Codex…")
        self.assertEqual(self.service.action_caption({"operation": "agent", "agent": "codex", "text": "x" * 80}), "Telling Codex: " + "x" * 60 + "…")
        self.assertEqual(self.service.action_caption({"operation": "agent", "agent": "claude", "text": "hi"}), "Telling Claude Code: hi")
        self.assertEqual(self.service.action_caption({"operation": "desktop", "application": "claude", "action": "close"}), "Closing Claude Code…")

    async def test_close_is_routed_and_captioned(self):
        seen = []
        async def close(application):
            seen.append((application, self.service.voice.get("action_caption")))
            return {"application": application, "status": "closed"}
        self.service.desktop.close.side_effect = close
        await self.service.conversation_action({"operation": "desktop", "application": "codex", "action": "close"}, "first")
        self.assertEqual(seen, [("codex", "Closing Codex…")])
        self.service.desktop.open.assert_not_awaited()
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "desktop", "application": "codex", "action": "kill"}, "first")
        self.assertEqual(self.service.action_label({"operation": "desktop", "application": "browser", "url": "https://x.example"}), "desktop browser url")
        self.assertEqual(self.service.action_label({"operation": "agent", "agent": "codex", "text": "secret words", "reply": ""}), "agent codex")

    async def test_agent_decisions_need_the_persons_own_answer(self):
        self.service.desktop.tell.return_value = {"agent": "claude", "status": "answered"}
        approve = {"operation": "agent", "agent": "claude", "text": "", "reply": "approve"}
        # The turn that asked Claude for work did not answer anything.
        with self.assertRaises(VoiceError) as raised:
            await self.service.conversation_action(approve, "first")
        self.assertEqual(raised.exception.code, "ANSWER_NOT_HEARD")
        self.service.desktop.tell.assert_not_awaited()
        await self.turn("ambiguous", "Don't approve that yet")
        with self.assertRaises(VoiceError):
            await self.service.conversation_action(approve, "ambiguous")
        await self.turn("yes", "Yes, go ahead")
        await self.service.conversation_action(approve, "yes")
        self.service.desktop.tell.assert_awaited_once_with("claude", "", "approve", title=None, busy_ok=True)
        await self.turn("no", "No, deny it")
        await self.service.conversation_action(approve | {"reply": "deny"}, "no")
        self.assertEqual(self.service.desktop.tell.await_count, 2)

    async def test_web_task_is_framed_by_the_daemon_and_followed(self):
        self.service.desktop.tell.return_value = {"agent": "web-1", "status": "sent"}
        watched = []
        self.service.watch_agent = watched.append
        words = "find cheap flights from Newark to Austin next week or the week after"
        result = await self.service.conversation_action({"operation": "agent", "agent": "codex", "kind": "web_task", "reply": "", "text": words}, "first")
        (seat, text, reply), options = self.service.desktop.tell.await_args
        self.assertEqual((seat, reply, result["job"]), ("web-1", "", "web-1"))
        self.assertEqual(options["title"], "Web: " + self.service.job_title(words))
        self.assertTrue(options["title"].endswith("…") and len(options["title"]) <= 53)
        self.assertIn("Today is ", text)
        self.assertIn("playwright", text)
        self.assertIn("never buy, book, sign in", text)
        self.assertTrue(text.endswith("Request: " + words))
        self.assertEqual(watched, ["web-1"])
        self.assertEqual(self.service.jobs["web-1"]["state"], "working")
        self.assertEqual(self.service.voice["action_caption"], "Starting web task: " + words[:60] + "…")
        with self.assertRaises(VoiceError):
            await self.service.conversation_action({"operation": "agent", "agent": "codex", "kind": "shell", "text": "x", "reply": ""}, "first")

    async def test_note_job_writes_a_brief_from_the_whole_conversation_and_starts_in_the_vault(self):
        vault = self.root / "Vault"
        vault.mkdir()
        self.service.notes_vault = lambda: vault
        self.service.desktop.tell.side_effect = lambda seat, *args, **kwargs: {"agent": seat, "status": "sent"}
        watched = []
        self.service.watch_agent = lambda seat, **options: watched.append((seat, options))
        note = {"operation": "note", "request": "write up this app idea and research how to launch it", "research": "yes"}
        await self.turn("short", "Save this")
        with self.assertRaises(VoiceError) as raised:
            await self.service.conversation_action(note, "short")
        self.assertEqual(raised.exception.code, "NOTE_NOTHING_TO_WRITE")
        await self.turn("rant", "I keep thinking about an app for dog walkers with lots of dogs that plans the best routes and parks for them")
        await self.service.provider_event({"type": "transcript", "role": "assistant", "text": "Who pays for it?", "final": True})
        await self.turn("ask", "Put all of that in Obsidian and research the market")
        result = await self.service.conversation_action(note, "ask")
        (seat, line), options = self.service.desktop.tell.await_args
        self.assertEqual((seat, result["job"], options["cwd"]), ("note-1", "note-1", vault))
        self.assertEqual(options["title"], "Note: " + self.service.job_title(note["request"]))
        brief = Path(line.split("brief at ", 1)[1].split(" and follow", 1)[0])
        self.assertEqual(brief.parent, self.root / "state" / "notes")
        text = brief.read_text()
        self.assertIn("Person: I keep thinking about an app for dog walkers", text)
        self.assertIn("Maslow: Who pays for it?", text)
        self.assertIn(note["request"], text)
        self.assertIn("The person asked for research", text)
        self.assertNotIn("Results from Maslow's background tasks", text)
        self.assertEqual(watched, [("note-1", {"limit": 45 * 60})])
        self.assertEqual(self.service.jobs["note-1"]["kind"], "note")
        self.assertEqual(self.service.job_name("note-1"), "The note \"" + self.service.job_title(note["request"]) + "\"")
        self.assertIn("Obsidian note note-1", self.service.briefing())
        self.assertTrue(self.service.voice["action_caption"].startswith("Writing an Obsidian note: "))
        # A second note takes the second seat; a third waits for one to finish.
        await self.service.conversation_action(note | {"request": "make my plan for today"}, "ask")
        with self.assertRaises(VoiceError) as raised:
            await self.service.conversation_action(note | {"request": "and another"}, "ask")
        self.assertEqual(raised.exception.code, "JOBS_FULL")
        for bad in ({"research": "maybe"}, {"request": " "}, {"extra": 1}):
            with self.assertRaises(VoiceError):
                await self.service.conversation_action(note | bad, "ask")

    async def test_first_note_in_a_vault_holds_its_instruction_until_trust_is_answered(self):
        vault = self.root / "Vault"
        vault.mkdir()
        self.service.notes_vault = lambda: vault
        trust = "Trust this folder? Codex can read, edit, and run files here"
        self.service.desktop.tell.side_effect = [{"agent": "note-1", "status": "needs_answer", "prompt": trust},
                                                 {"agent": "note-1", "status": "answered", "reply": "approve"},
                                                 {"agent": "note-1", "status": "sent"}]
        self.service.desktop.agent_state.return_value = {"state": "idle"}
        watched = []
        self.service.watch_agent = lambda seat, **options: watched.append(seat)
        await self.turn("rant", "Plan my week around the launch, the hiring calls and finally fixing my sleep schedule please")
        result = await self.service.conversation_action({"operation": "note", "request": "plan my week", "research": "no"}, "rant")
        self.assertEqual((result["status"], self.service.jobs["note-1"]["state"]), ("needs_answer", "waiting"))
        self.assertIn("reply approve and job note-1", result["note"])
        instruction = self.service.jobs["note-1"]["pending"]
        self.assertEqual(watched, [])
        await self.turn("yes", "Yes, trust it")
        result = await self.service.conversation_action({"operation": "agent", "agent": "codex", "text": "", "reply": "approve", "job": "note-1"}, "yes")
        self.assertIn("job has started", result["note"])
        self.assertEqual(self.service.desktop.tell.await_args.args[:2], ("note-1", instruction))
        self.assertNotIn("pending", self.service.jobs["note-1"])
        self.assertEqual((watched, self.service.jobs["note-1"]["state"]), (["note-1"], "working"))

    async def test_declined_trust_ends_the_note_job(self):
        vault = self.root / "Vault"
        vault.mkdir()
        self.service.notes_vault = lambda: vault
        self.service.desktop.tell.side_effect = [{"agent": "note-1", "status": "needs_answer", "prompt": "Trust this folder?"},
                                                 {"agent": "note-1", "status": "answered", "reply": "deny"}]
        await self.turn("rant", "Plan my week around the launch, the hiring calls and finally fixing my sleep schedule please")
        await self.service.conversation_action({"operation": "note", "request": "plan my week", "research": "no"}, "rant")
        await self.turn("no", "No, don't")
        result = await self.service.conversation_action({"operation": "agent", "agent": "codex", "text": "", "reply": "deny", "job": "note-1"}, "no")
        self.assertEqual(result["note"], "The job was not started.")
        self.service.desktop.end_seat.assert_awaited_once_with("note-1")
        self.assertNotIn("note-1", self.service.jobs)

    async def test_note_brief_includes_recent_web_task_results(self):
        vault = self.root / "Vault"
        vault.mkdir()
        self.service.notes_vault = lambda: vault
        self.service.desktop.tell.return_value = {"agent": "note-1", "status": "sent"}
        self.service.watch_agent = lambda seat, **options: None
        now = time.time()
        self.service.jobs["web-1"] = {"id": "web-1", "kind": "web", "title": "research dog apps", "state": "finished",
                                      "started": now - 300, "updated": now - 60, "result": "• Top apps: Pupford, Dogo. https://dogo.app"}
        self.service.jobs["web-2"] = {"id": "web-2", "kind": "web", "title": "old search", "state": "finished",
                                      "started": now - 9000, "updated": now - 7200, "result": "stale answer"}
        self.service.jobs["web-3"] = {"id": "web-3", "kind": "web", "title": "still going", "state": "working",
                                      "started": now - 30, "updated": now - 5, "result": ""}
        await self.turn("ask", "Write up the dog app idea with everything the web search found")
        await self.service.conversation_action({"operation": "note", "request": "write up the dog app idea", "research": "auto"}, "ask")
        line = self.service.desktop.tell.await_args.args[1]
        text = Path(line.split("brief at ", 1)[1].split(" and follow", 1)[0]).read_text()
        self.assertIn("Results from Maslow's background tasks", text)
        self.assertIn("### research dog apps", text)
        self.assertIn("Top apps: Pupford, Dogo. https://dogo.app", text)
        self.assertNotIn("stale answer", text)
        self.assertNotIn("still going", text)

    async def test_note_covers_a_conversation_that_just_ended(self):
        vault = self.root / "Vault"
        vault.mkdir()
        self.service.notes_vault = lambda: vault
        await self.turn("rant", "Today I need to finish the investor deck, call the accountant and stop doom scrolling at night")
        await self.service.end_voice()
        await self.service.start_voice(audio=False)
        await self.turn("ask", "Turn what I said earlier into my plan for today")
        self.service.desktop = AsyncMock()
        self.service.desktop.tell.return_value = {"agent": "note-1", "status": "sent"}
        self.service.watch_agent = lambda seat, **options: None
        await self.service.conversation_action({"operation": "note", "request": "my plan for today", "research": "no"}, "ask")
        line = self.service.desktop.tell.await_args.args[1]
        text = Path(line.split("brief at ", 1)[1].split(" and follow", 1)[0]).read_text()
        self.assertIn("finish the investor deck", text)
        self.assertIn("Turn what I said earlier into my plan for today", text)

    async def test_separate_web_tasks_get_separate_seats_and_corrections_stay_with_their_job(self):
        self.service.desktop.tell.side_effect = lambda seat, *args, **kwargs: {"agent": seat, "status": "sent"}
        self.service.watch_agent = lambda seat: None
        web = {"operation": "agent", "agent": "codex", "kind": "web_task", "reply": ""}
        await self.turn("flights", "Find cheap flights to Austin")
        await self.service.conversation_action(web | {"text": "find cheap flights to Austin"}, "flights")
        await self.turn("activities", "Find activities to do in Austin")
        await self.service.conversation_action(web | {"text": "find activities to do in Austin"}, "activities")
        self.assertEqual(sorted(self.service.jobs), ["web-1", "web-2"])
        await self.turn("dallas", "Make the flights Dallas instead")
        await self.service.conversation_action(web | {"text": "make it Dallas instead", "job": "web-1"}, "dallas")
        (seat, text, _), options = self.service.desktop.tell.await_args
        # A correction goes to its own job, unframed, and may redirect that work.
        self.assertEqual((seat, text, options["busy_ok"]), ("web-1", "make it Dallas instead", True))
        watched = []
        self.service.watch_agent = watched.append
        self.service.jobs["web-1"]["state"] = "finished"
        await self.turn("return", "Add a return trip to the flight search")
        await self.service.conversation_action(web | {"text": "add a return trip", "job": "web-1"}, "return")
        # The follow-up's result is reported too.
        self.assertEqual((watched, self.service.jobs["web-1"]["state"]), (["web-1"], "working"))
        self.service.watch_agent = lambda seat: None
        await self.turn("third", "Find hotels in Austin")
        await self.service.conversation_action(web | {"text": "find hotels in Austin"}, "third")
        await self.turn("fourth", "Find restaurants in Austin")
        with self.assertRaises(VoiceError) as raised:
            await self.service.conversation_action(web | {"text": "find restaurants in Austin"}, "fourth")
        self.assertEqual(raised.exception.code, "JOBS_FULL")
        # A finished job's seat is ended and reused for the next task.
        self.service.jobs["web-2"]["state"] = "finished"
        await self.service.conversation_action(web | {"text": "find restaurants in Austin"}, "fourth")
        self.service.desktop.end_seat.assert_awaited_once_with("web-2")
        self.assertEqual(self.service.jobs["web-2"]["title"], "find restaurants in Austin")
        with self.assertRaises(VoiceError) as raised:
            await self.service.conversation_action(web | {"text": "x", "job": "web-9"}, "fourth")
        self.assertEqual(raised.exception.code, "JOB_NOT_FOUND")

    async def test_status_lists_every_job_by_name_and_is_always_fresh(self):
        self.service.jobs["web-1"] = {"id": "web-1", "title": "find cheap flights", "state": "working", "started": 0, "updated": 0, "result": ""}
        states = {"web-1": {"state": "working", "screen": "• Working"}, "codex": {"state": "idle", "screen": "› Ask"}, "claude": {"state": "closed"}}
        self.service.desktop.agent_state.side_effect = lambda seat: states[seat]
        for _ in range(2):
            result = await self.service.conversation_action({"operation": "agent_status"}, "first")
        self.assertEqual([(job["job"], job["title"], job["state"]) for job in result["jobs"]],
                         [("web-1", "find cheap flights", "working"), ("codex", "Codex", "idle")])
        self.assertEqual(self.service.desktop.agent_state.await_count, 6)

    async def test_show_opens_a_viewer_on_the_named_job(self):
        self.service.jobs["web-1"] = {"id": "web-1", "title": "find cheap flights", "state": "working", "started": 0, "updated": 0, "result": ""}
        self.service.desktop.agent_state.return_value = {"state": "working", "screen": "• Working"}
        await self.service.conversation_action({"operation": "agent_status", "job": "web-1", "show": True}, "first")
        self.service.desktop.open.assert_awaited_with("web-1", title="Web: find cheap flights", view=True)
        self.assertEqual(self.service.voice["action_caption"], "Showing find cheap flights…")

    async def test_conversation_libraries_are_loaded_before_the_first_click(self):
        loaded = []
        async def to_thread(function):
            loaded.append(function)
        with patch("maslow_voice.daemon.asyncio.to_thread", to_thread):
            await self.service.warm_conversation()
            self.service.settings.value["mode"] = "openai"
            await self.service.warm_conversation()
        self.assertEqual(len(loaded), 1)
        loaded[0]()  # The real imports succeed in the pinned environment.

    async def test_new_conversation_is_briefed_on_tasks_and_the_last_exchange(self):
        self.service.jobs["web-1"] = {"id": "web-1", "title": "find cheap flights", "state": "working", "started": 0, "updated": 0, "result": ""}
        self.service.session["transcript"] = [{"role": "user", "text": "Find cheap flights to Austin"}, {"role": "assistant", "text": "Searching now."}]
        await self.service.end_voice()
        briefing = self.service.briefing()
        self.assertIn('Web task web-1 "find cheap flights": working', briefing)
        self.assertIn("user: Find cheap flights to Austin", briefing)
        self.assertIn("agent_status", briefing)
        self.service.last_conversation["ended"] -= 3600
        self.assertNotIn("Find cheap flights to Austin", self.service.briefing())

    async def test_an_old_finished_task_is_not_the_current_task(self):
        task, _ = self.service.store.create("old-request", dict(BRIEF), str(self.root), "gemini_live", "Build a tracker")
        task = self.service.store.update(task["id"], state="completed") or self.service.store.get(task["id"])
        self.assertEqual(self.service.current_task()["id"], task["id"])
        later = task["updated_at"] + 7200
        with patch("maslow_voice.daemon.time.time", return_value=later):
            with self.assertRaises(VoiceError) as raised:
                self.service.current_task()
            self.service.current_task_id = task["id"]
            with self.assertRaises(VoiceError):
                self.service.current_task()
        self.assertEqual(raised.exception.code, "TASK_NOT_FOUND")

    async def test_watcher_announces_decisions_once_and_the_finished_answer(self):
        states = [{"state": "working"}, {"state": "waiting", "prompt": "Allow the playwright MCP server"},
                  {"state": "waiting", "prompt": "Allow the playwright MCP server"}, {"state": "working"},
                  {"state": "idle", "screen": "Cheapest: $142"}, {"state": "idle", "screen": "Cheapest: $142"}]
        self.service.desktop.agent_state.side_effect = states
        notices = []
        async def notice(agent, state, screen):
            notices.append((agent, state, screen))
        self.service.agent_notice = notice
        self.service.agent_jobs.add("codex")
        await self.service._watch_agent("codex", interval=0)
        self.assertEqual(notices, [("codex", "waiting for a decision", "Allow the playwright MCP server"), ("codex", "finished", "Cheapest: $142")])
        self.assertNotIn("codex", self.service.agent_jobs)

    async def test_a_spoken_result_is_also_notified_and_leaves_time_to_answer(self):
        self.service.provider.notify_task = AsyncMock(return_value=True)
        self.service.jobs["web-1"] = {"id": "web-1", "title": "find cheap flights", "state": "finished", "started": 0, "updated": 0, "result": ""}
        self.service.last_activity = 0
        await self.service.agent_notice("web-1", "finished", "› find cheap flights\n• Cheapest is **$337** on Alaska, Oct 20–27.")
        self.service.desktop.run.assert_awaited_once_with("omarchy-notification-send", "--app-name", "Maslow Voice",
                                                          'The task "find cheap flights" has finished', "Cheapest is $337 on Alaska, Oct 20–27.")
        self.service.provider.notify_task.assert_awaited_once()
        self.assertGreater(self.service.last_activity, 0)
        self.assertFalse(self.service.session_expired())

    def test_answer_line_skips_progress_and_interface_text(self):
        screen = ("› Web task from Maslow Voice. Request: find flights\n• I’ll compare flights.\n• Explored\n  └ List files\n"
                  "• The cheapest option is **$324** nonstop on United, Oct 11.\n  | Flight | Price |")
        self.assertEqual(self.service.answer_line(screen), "The cheapest option is $324 nonstop on United, Oct 11.")
        self.assertEqual(self.service.answer_line(""), "")

    async def test_finished_notice_without_a_conversation_is_still_notified(self):
        self.service.provider = None
        await self.service.agent_notice("codex", "finished", "• All tests pass.")
        self.service.desktop.run.assert_awaited_once_with("omarchy-notification-send", "--app-name", "Maslow Voice",
                                                          "Codex has finished", "All tests pass.")

    def test_running_agent_keeps_a_quiet_conversation_open(self):
        quiet = self.service.last_activity + self.service.settings.value["idle_seconds"] + 5
        self.service.session_started = quiet - 60
        self.assertTrue(self.service.session_expired(now=quiet))
        self.service.agent_jobs.add("codex")
        self.assertFalse(self.service.session_expired(now=quiet))
        self.assertTrue(self.service.session_expired(now=self.service.session_started + 30 * 60))

    async def test_slow_action_answers_quickly_and_reports_only_failures_or_questions(self):
        notices = []
        async def notice(content):
            notices.append(content)
            return "sent to the conversation"
        self.service.conversation_notice = notice
        release = asyncio.Event()
        async def slow_open(application, url=None):
            await release.wait()
            return {"application": application, "status": "opened"}
        self.service.desktop.open.side_effect = slow_open
        started = time.monotonic()
        result = await self.service.conversation_action({"operation": "desktop", "application": "browser"}, "first")
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual((result["status"], result["verification"]), ("started", "in_progress"))
        # A retry of the same call gets the same receipt and launches nothing new.
        self.assertEqual(await self.service.conversation_action({"operation": "desktop", "application": "browser"}, "first"), result)
        self.assertEqual(self.service.desktop.open.await_count, 1)
        release.set()
        await asyncio.sleep(0)
        await asyncio.gather(*self.service.work, return_exceptions=True)
        self.assertEqual(notices, [], "A successful action says nothing more")

        async def slow_failure(application, url=None):
            await asyncio.sleep(1)
            raise VoiceError("APPLICATION_NOT_OBSERVED", "The window did not appear.")
        self.service.desktop.open.side_effect = slow_failure
        await self.turn("files", "Open Files")
        result = await self.service.conversation_action({"operation": "desktop", "application": "files"}, "files")
        self.assertEqual(result["status"], "started")
        await asyncio.sleep(1.2)
        self.assertEqual(notices[-1]["state"], "failed")
        self.assertEqual(notices[-1]["reason"], "The window did not appear.")
        self.assertEqual(notices[-1]["action"], "Opening Files")

        async def slow_question(seat, *args, **kwargs):
            await asyncio.sleep(1)
            return {"agent": seat, "status": "needs_answer", "prompt": "Trust this folder?"}
        self.service.desktop.tell.side_effect = slow_question
        self.service.notes_vault = lambda: self.root
        await self.turn("rant", "Plan my week around the launch, the hiring calls and finally fixing my sleep schedule please")
        result = await self.service.conversation_action({"operation": "note", "request": "plan my week", "research": "no"}, "rant")
        self.assertEqual(result["status"], "started")
        await asyncio.sleep(1.2)
        self.assertEqual((notices[-1]["state"], notices[-1]["prompt"]), ("waiting for the person's answer", "Trust this folder?"))
        self.assertIn("reply approve and job note-1", notices[-1]["note"])
        self.assertEqual(self.service.jobs["note-1"]["state"], "waiting")

    def test_final_answer_is_the_closing_message_without_tool_activity(self):
        screen = """• Browsing the web
• Searched the web for dog walking software pricing
• Edited 2 files (+184 -0)
  └ Research/Dog walker - Research.md (+121 -0)
• Ran python - <<'PY' …
  └ Checked structure
• Saved Voice Notes/2026-10-04 Dog walker idea.md
  Your focus is the orb testing. I added a linked research note
  with competitors and pricing.
  Worked for 2m 36s · 4:12 PM
                                  Tip: Use /status to see the current model"""
        self.assertEqual(VoiceService.final_answer(screen),
                         "Saved Voice Notes/2026-10-04 Dog walker idea.md Your focus is the orb testing. I added a linked research note with competitors and pricing.")
        self.assertEqual(VoiceService.final_answer("• Working (3s • esc to interrupt)"), "• Working (3s • esc to interrupt)")
        self.assertLessEqual(len(VoiceService.final_answer("• " + "word " * 500)), 900)

    async def test_dropped_gemini_session_reconnects_with_the_conversation(self):
        await self.service.provider_event({"type": "transcript", "role": "assistant", "text": "Which park do you mean?", "final": True})
        self.service.voice["extended"] = True
        self.service.session_started -= 60
        first, session = self.service.provider, self.service.session["id"]
        configs = []
        original = self.service.provider_factory
        def factory(config, *args):
            configs.append(config)
            return original(config, *args)
        self.service.provider_factory = factory
        await self.service.provider_event({"type": "error", "code": "GEMINI_CONNECTION_FAILED", "message": "Gemini Voice disconnected."})
        await asyncio.gather(*self.service.work, return_exceptions=True)
        self.assertIsNot(self.service.provider, first)
        self.assertIsNotNone(self.service.provider)
        self.assertEqual((self.service.voice["error"], self.service.voice["extended"], self.service.voice["enabled"]), ("", True, False))
        self.assertNotIn("action_caption", self.service.voice)
        self.assertEqual(self.service.session["id"], session, "The same conversation continues")
        self.assertIn("Which park do you mean?", [line["text"] for line in self.service.session["transcript"]])
        briefing = configs[-1]["voice_briefing"]
        self.assertIn("has been restored", briefing)
        self.assertIn("do not greet the person", briefing)
        self.assertIn("assistant: Which park do you mean?", briefing)
        self.assertNotIn("has been restored", self.service.briefing())
        # Later drops reconnect too, until every attempt in the window is used.
        with patch("maslow_voice.daemon.RECONNECT_DELAYS", (0, 0, 0, 0)):
            for expected in (False, False, False, True):
                await self.service.provider_event({"type": "error", "code": "GEMINI_CONNECTION_FAILED", "message": "Gemini Voice disconnected."})
                await asyncio.gather(*self.service.work, return_exceptions=True)
                self.assertEqual(self.service.provider is None, expected)
        self.assertEqual(self.service.voice["error"], "Gemini Voice disconnected.")

    async def test_drop_right_after_start_is_retried_but_setup_and_audio_errors_are_not(self):
        # Gemini's connection opens after start returns, so its failure can
        # arrive at once; it is as momentary as a later drop.
        self.service.session_started = time.monotonic()
        await self.service.provider_event({"type": "error", "code": "GEMINI_CONNECTION_FAILED", "message": "Gemini Voice disconnected."})
        await asyncio.gather(*self.service.work, return_exceptions=True)
        self.assertIsNotNone(self.service.provider)
        self.assertEqual(len(self.service.reconnects), 1)
        for code in ("GEMINI_SETUP_REJECTED", "AUDIO_FAILED"):
            if not self.service.provider:
                await self.service.start_voice(audio=False)
            await self.service.provider_event({"type": "error", "code": code, "message": "Voice needs attention."})
            await asyncio.gather(*self.service.work, return_exceptions=True)
            self.assertIsNone(self.service.provider, code)
            self.assertEqual(self.service.voice["error"], "Voice needs attention.")
        self.assertEqual(len(self.service.reconnects), 1)

    def flaky_factory(self, failures, code="GEMINI_CONNECTION_FAILED"):
        """A provider factory whose first starts fail the way Gemini's do."""
        attempts = []
        class Flaky(FakeProvider):
            async def start(self, audio=True):
                attempts.append(code)
                if len(attempts) <= failures:
                    await self.emit({"type": "voice_state", "state": "connecting", "microphone": False})
                    await self.emit({"type": "error", "code": code, "message": "Gemini Voice disconnected."})
                    raise VoiceError(code, "Gemini Voice disconnected.")
                await super().start(audio)
        self.service.provider_factory = Flaky
        return attempts

    async def test_failed_start_is_retried_quietly_until_it_connects(self):
        await self.service.end_voice()
        attempts = self.flaky_factory(2)
        captions = []
        original = self.service.publish
        async def publish():
            captions.append((self.service.voice["state"], self.service.voice.get("action_caption")))
            await original()
        self.service.publish = publish
        self.service.internet_ready = AsyncMock(return_value=True)
        with patch("maslow_voice.daemon.RECONNECT_DELAYS", (0, 0, 0, 0)):
            await self.service.dispatch({"action": "start_voice"})
        self.assertEqual(len(attempts), 3)
        self.assertIsNotNone(self.service.provider)
        self.assertEqual(self.service.voice["error"], "")
        self.assertNotIn("action_caption", self.service.voice)
        self.assertIn(("connecting", "Connecting…"), captions)

    async def test_start_reports_the_failure_after_the_last_attempt(self):
        await self.service.end_voice()
        attempts = self.flaky_factory(10)
        self.service.internet_ready = AsyncMock(return_value=True)
        with patch("maslow_voice.daemon.RECONNECT_DELAYS", (0, 0, 0, 0)):
            with self.assertRaises(VoiceError):
                await self.service.dispatch({"action": "start_voice"})
        self.assertEqual(len(attempts), 4)
        self.assertIsNone(self.service.provider)
        self.assertEqual(self.service.voice["error"], "Gemini Voice disconnected.")
        self.assertNotIn("action_caption", self.service.voice)

    async def test_rejected_setup_is_not_retried(self):
        await self.service.end_voice()
        attempts = self.flaky_factory(10, "GEMINI_SETUP_REJECTED")
        # The error event ends Voice at once, which cancels the start request.
        with self.assertRaises((VoiceError, asyncio.CancelledError)):
            await self.service.dispatch({"action": "start_voice"})
        await asyncio.gather(*self.service.work, return_exceptions=True)
        self.assertEqual(len(attempts), 1)
        self.assertIsNone(self.service.provider)
        self.assertEqual(self.service.voice["error"], "Gemini Voice disconnected.")

    async def test_start_waits_for_internet_before_retrying(self):
        await self.service.end_voice()
        attempts = self.flaky_factory(1)
        self.service.internet_ready = AsyncMock(side_effect=[False, True])
        captions = []
        original = self.service.publish
        async def publish():
            captions.append(self.service.voice.get("action_caption"))
            await original()
        self.service.publish = publish
        with patch("maslow_voice.daemon.RECONNECT_DELAYS", (0, 0, 0, 0)):
            await self.service.dispatch({"action": "start_voice"})
        self.assertEqual(len(attempts), 2)
        self.assertIn("Waiting for internet…", captions)
        self.assertNotIn("action_caption", self.service.voice)

    async def test_ending_voice_during_the_reconnect_pause_stays_ended(self):
        self.service.session_started -= 60
        with patch("maslow_voice.daemon.RECONNECT_DELAYS", (5, 5, 5, 5)):
            await self.service.provider_event({"type": "error", "code": "GEMINI_CONNECTION_FAILED", "message": "Gemini Voice disconnected."})
            await asyncio.sleep(0.05)
            self.assertEqual((self.service.voice["state"], self.service.voice.get("action_caption")), ("connecting", "Reconnecting…"))
            await self.service.end_voice()
            await asyncio.gather(*self.service.work, return_exceptions=True)
        self.assertIsNone(self.service.provider)
        self.assertEqual(self.service.voice["state"], "disabled")
        self.assertNotIn("action_caption", self.service.voice)

    async def test_action_caption_fades_even_after_failure(self):
        seen = []
        async def fail(application, url=None):
            seen.append(self.service.voice.get("action_caption"))
            raise VoiceError("APPLICATION_NOT_OBSERVED", "no window")
        self.service.desktop.open.side_effect = fail
        real_sleep = asyncio.sleep
        async def yield_once(*_):
            await real_sleep(0)
        # Each fade wait yields once, so the action still runs before it ends.
        with patch("maslow_voice.daemon.asyncio.sleep", AsyncMock(side_effect=yield_once)):
            with self.assertRaises(VoiceError):
                await self.service.conversation_action({"operation": "desktop", "application": "files"}, "first")
            self.assertEqual(seen, ["Opening Files…"])
            await asyncio.gather(*self.service.work)
        self.assertNotIn("action_caption", self.service.voice)

    async def test_workspace_auto_dedup_and_passive_attention(self):
        initial_view = dict(self.service.task_view_request)
        result = await self.service.conversation_action(BRIEF, "first")
        duplicate = await self.service.conversation_action(dict(BRIEF, summary="Paraphrased"), "first")
        self.assertEqual(result["id"], duplicate["id"])
        self.assertTrue(Path(result["project"]).is_dir())
        self.assertEqual(self.service.snapshot()["task_view_request"], initial_view)
        self.assertEqual(self.service.snapshot()["task_attention"]["task_id"], result["id"])
        await self.turn("show", "Show my task")
        await self.service.conversation_action({"operation": "task", "action": "show"}, "show")
        self.assertEqual(self.service.task_view_request["task_id"], result["id"])
        self.assertEqual(self.service.task_view_request["sequence"], initial_view["sequence"] + 1)
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

    async def two_completed_tasks(self):
        first = await self.service.conversation_action(BRIEF, "first")
        first = self.service.store.update(first["id"], state="completed")
        second, _ = self.service.store.create("other-task", BRIEF, first["project"], "gemini_live", "Another request")
        second = self.service.store.update(second["id"], state="completed")
        return first, second

    async def test_delayed_typed_and_spoken_actions_keep_captured_task(self):
        first, second = await self.two_completed_tasks()
        self.service.tasks.action = AsyncMock(return_value=first)
        for source in ("typed", "spoken"):
            for action in ("status", "show", "show_result", "steer", "cancel", "continue"):
                with self.subTest(source=source, action=action):
                    await self.service.dispatch({"action": "task_action", "id": first["id"], "operation": "select"})
                    words = source + " " + action
                    identity = "turn-" + words
                    if source == "typed":
                        await self.service.dispatch({"action": "submit_text", "text": words})
                    else:
                        await self.service.provider.emit({"type": "transcript", "role": "user", "text": words,
                                                          "turn_id": identity, "final": True})
                    await self.service.dispatch({"action": "task_action", "id": second["id"], "operation": "select"})
                    # A repeated transcript callback must not recapture selection.
                    await self.turn(identity, words)
                    result = await self.service.provider.submit({"operation": "task", "action": action, "text": words}, identity)
                    self.assertEqual(result["id"], first["id"])
                    if action in {"steer", "cancel", "continue"}:
                        self.service.tasks.action.assert_awaited_with(first["id"], action, words)

    async def test_ambiguous_target_cannot_follow_later_selection(self):
        first, second = await self.two_completed_tasks()
        self.service.current_task_id = ""
        self.service.store.update(first["id"], state="queued")
        self.service.store.update(second["id"], state="queued")
        await self.turn("ambiguous", "Stop the task")
        await self.service.dispatch({"action": "task_action", "id": second["id"], "operation": "select"})
        self.service.tasks.action = AsyncMock()
        with self.assertRaises(VoiceError) as raised:
            await self.service.provider.submit({"operation": "task", "action": "cancel"}, "ambiguous")
        self.assertEqual(raised.exception.code, "TASK_AMBIGUOUS")
        self.service.tasks.action.assert_not_awaited()

    async def test_task_created_by_another_turn_does_not_bind_empty_capture(self):
        await self.turn("earlier", "Stop the task")
        await self.service.conversation_action(BRIEF, "first")
        self.service.tasks.action = AsyncMock()
        with self.assertRaises(VoiceError) as raised:
            await self.service.provider.submit({"operation": "task", "action": "cancel"}, "earlier")
        self.assertEqual(raised.exception.code, "TASK_NOT_FOUND")
        self.service.tasks.action.assert_not_awaited()

    async def test_same_turn_submission_receipt_binds_new_task_despite_selection(self):
        first, second = await self.two_completed_tasks()
        await self.service.request_task_view(first["id"])
        await self.turn("new-task", "Build another app, then show its status")
        payload = {"operation": "submit", "brief": BRIEF, "new_project": True}
        created = await self.service.provider.submit(payload, "new-task")
        await self.service.request_task_view(second["id"])
        # Exercise both cached and paraphrased submission retries.
        await self.service.provider.submit(payload, "new-task")
        await self.service.provider.submit(dict(BRIEF, summary="Paraphrased"), "new-task")
        result = await self.service.provider.submit({"operation": "task", "action": "status"}, "new-task")
        self.assertEqual(result["id"], created["id"])
        self.assertNotIn(result["id"], (first["id"], second["id"]))
        self.assertEqual(len(self.service.store.list()), 3)

    async def test_old_provider_action_waiting_on_lock_cannot_use_new_turn(self):
        first, second = await self.two_completed_tasks()
        await self.service.request_task_view(first["id"])
        await self.turn("reused-id", "Stop the task")
        self.service.tasks.action = AsyncMock()
        async with self.service.action_lock:
            pending = asyncio.create_task(self.service.provider.submit({"operation": "task", "action": "cancel"}, "reused-id"))
            await asyncio.sleep(0)
            await self.service.end_voice()
            await self.service.start_voice(audio=False)
            await self.service.request_task_view(second["id"])
            await self.turn("reused-id", "Stop the task")
        with self.assertRaises(VoiceError) as raised:
            await pending
        self.assertEqual(raised.exception.code, "TURN_ENDED")
        self.service.tasks.action.assert_not_awaited()

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
