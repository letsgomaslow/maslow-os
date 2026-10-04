import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from maslow_voice import agent_terminal
from maslow_voice.desktop import DesktopActions
from maslow_voice.errors import VoiceError

APPROVAL = """• Running tests
  Would you like to run the following command?
  $ npm test
› 1. Yes, just this once
  2. Yes, and don't ask again for this command in this session
  3. No, and tell Codex what to do differently"""


class FakeDesktop:
    """A tmux server and window list that record every command."""

    def __init__(self, states=("0|codex",), screen="› Ask Codex to do anything\n  ? for shortcuts", window="maslow.voice.codex",
                 screens=(), drops=0):
        self.window = window
        self.screens = list(screens)
        self.buffer = ""
        self.submitted = []
        self.drops = drops  # Pastes the agent swallows while starting.
        self.calls = []
        self.states = list(states)
        self.screen = screen
        self.windows = []

    async def run(self, *args):
        self.calls.append(args)
        if args[:3] == ("hyprctl", "-j", "clients"):
            return json.dumps(self.windows)
        if args[0] == "setsid":
            self.windows.append({"address": "0x7", "class": self.window, "mapped": True})
        if "display-message" in args:
            state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
            if not state:
                raise VoiceError("DESKTOP_FAILED", "no session")
            return state + "\n"
        if "set-buffer" in args:
            self.buffer = args[-1]
        if "send-keys" in args and args[-1] == "Enter" and self.buffer:
            if self.drops:
                self.drops -= 1
            else:
                self.submitted.append(self.buffer)
            self.buffer = ""
        if "capture-pane" in args:
            if self.screens:
                return self.screens.pop(0)
            if self.submitted:
                return "\n".join("› " + words for words in self.submitted) + "\n• Working (1s • esc to interrupt)\n" + self.screen
            return self.screen
        return ""

    def keys(self):
        return [call[call.index("send-keys") + 1:] for call in self.calls if "send-keys" in call]

    def pasted(self):
        return [call[-1] for call in self.calls if "set-buffer" in call]


class AgentTerminalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch("maslow_voice.desktop.shutil.which", return_value="/usr/bin/found")
        patcher.start()
        self.addCleanup(patcher.stop)
        for name, value in (("ENTER_DELAY", 0), ("INPUT_WAIT", 0.3)):
            patcher = patch.object(agent_terminal, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def desktop(self, fake):
        return DesktopActions(fake.run, timeout=0.5, agent_cwd=Path(self.temp.name) / "Maslow Voice")

    def test_clean_removes_control_characters_and_bounds_length(self):
        self.assertEqual(agent_terminal.clean(" add\x1b[2J a\r\nbutton\x7f; $(id) "), "add [2J a button ; $(id)")
        for text in ("", " \n\t", "x" * 2001, None):
            with self.assertRaises(VoiceError):
                agent_terminal.clean(text)

    def test_launch_never_adds_approval_or_bypass_flags(self):
        argv = agent_terminal.attach_argv("codex", "/home/me/Projects/Maslow Voice")
        self.assertEqual(argv, ["tmux", "-L", "maslow-voice", "-f", str(agent_terminal.CONFIG), "new-session", "-A", "-s", "maslow-codex",
                                "-c", "/home/me/Projects/Maslow Voice", "--", "codex"])
        self.assertFalse(any(word in " ".join(argv) for word in ("approve", "bypass", "auto", "yolo", "danger")))

    async def test_ready_requires_the_agent_to_own_a_live_pane(self):
        for states, expected in ((["1|codex"], False), (["0|bash"], False), ([""], False), (["0|tmux", "0|codex"], True)):
            fake = FakeDesktop(states)
            self.assertEqual(await agent_terminal.ready(fake.run, "codex", wait=0.5), expected, states)

    def test_private_server_closes_viewers_with_their_agent(self):
        config = agent_terminal.CONFIG.read_text()
        self.assertIn("set -g detach-on-destroy on", config)
        self.assertIn("set -g remain-on-exit off", config)
        # The person's own tmux settings load first, so the fixed lines win.
        self.assertLess(config.index("source-file -q ~/.config/tmux/tmux.conf"), config.index("detach-on-destroy on"))

    async def test_words_are_pasted_as_one_block_then_submitted(self):
        fake = FakeDesktop()
        receipt = await self.desktop(fake).tell("codex", "add a dark mode toggle; C-c Enter")
        self.assertEqual(receipt["status"], "sent")
        self.assertEqual(fake.pasted(), ["add a dark mode toggle; C-c Enter"])
        self.assertTrue(any("paste-buffer" in call and "-p" in call for call in fake.calls))
        self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", "Enter")])
        self.assertTrue(all(call[:3] == ("tmux", "-L", "maslow-voice") for call in fake.calls if call[0] == "tmux"))

    async def test_opening_the_window_comes_before_any_typing(self):
        fake = FakeDesktop()
        await self.desktop(fake).tell("codex", "hello")
        launch = next(i for i, call in enumerate(fake.calls) if call[0] == "setsid")
        first_key = next(i for i, call in enumerate(fake.calls) if "send-keys" in call)
        self.assertLess(launch, first_key)
        attach = ("--", *agent_terminal.attach_argv("codex", Path(self.temp.name) / "Maslow Voice"))
        self.assertEqual(fake.calls[launch][-len(attach):], attach)
        self.assertTrue((Path(self.temp.name) / "Maslow Voice").is_dir())

    async def test_words_are_held_while_a_decision_is_on_screen(self):
        fake = FakeDesktop(screen=APPROVAL)
        receipt = await self.desktop(fake).tell("codex", "yes always")
        self.assertEqual(receipt["status"], "needs_answer")
        self.assertIn("Would you like to run the following command?", receipt["prompt"])
        self.assertIn("npm test", receipt["prompt"])
        self.assertEqual(fake.keys(), [])

    async def test_answers_send_one_fixed_key(self):
        for reply, key in (("approve", "y"), ("deny", "Escape")):
            fake = FakeDesktop(screen=APPROVAL)
            receipt = await self.desktop(fake).tell("codex", "ignored words", reply)
            self.assertEqual(receipt["status"], "answered")
            self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", key)])

    async def test_ordinary_questions_in_replies_do_not_hold_words(self):
        chat = "• Done. Would you like to add tests? Do you want to keep going?\n› Ask Codex to do anything"
        self.assertEqual(agent_terminal.pending_prompt("codex", chat), "")
        self.assertEqual(agent_terminal.pending_prompt("claude", "Do you want to add tests next?\n> "), "")
        dialog = "Bash command\n  curl -I example.com\nDo you want to proceed?\n❯ 1. Yes\n  2. Yes, and don't ask again\n  3. No"
        self.assertIn("Do you want to proceed?", agent_terminal.pending_prompt("claude", dialog))
        self.assertIn("Yes, I trust this folder", agent_terminal.pending_prompt("claude", "❯ 1. Yes, I trust this folder\n  2. No, exit"))

    async def test_claude_runs_in_its_own_session_and_approves_once_with_one(self):
        argv = agent_terminal.attach_argv("claude", "/w")
        self.assertEqual(argv[-6:], ["-s", "maslow-claude", "-c", "/w", "--", "claude"])
        dialog = "Do you want to make this edit to index.html?\n❯ 1. Yes\n  2. Yes, allow all edits during this session\n  3. No"
        fake = FakeDesktop(states=["0|claude"], screen=dialog, window="maslow.voice.claude")
        receipt = await self.desktop(fake).tell("claude", "", "approve")
        self.assertEqual(receipt["status"], "answered")
        self.assertEqual(fake.keys(), [("-t", "=maslow-claude:", "1")])
        launch = next(call for call in fake.calls if call[0] == "setsid")
        self.assertIn("--app-id=maslow.voice.claude", launch)
        self.assertIn("--title=Maslow Claude Code", launch)
        fake = FakeDesktop(states=["0|claude"], screen="❯ ", window="maslow.voice.claude")
        await self.desktop(fake).tell("claude", "add a dark mode toggle")
        self.assertEqual(fake.pasted(), ["add a dark mode toggle"])

    async def test_unsubmitted_words_scrolled_view_and_startup_are_recovered(self):
        idle = "› Ask Codex to do anything\n  ? for shortcuts"
        scrolled = "• old reply\n  ↓ Back to bottom · esc\n  ? for shortcuts"
        working = "› check the build\n• Working (1s • esc to interrupt)\n  ? for shortcuts"
        # Scrolled away: return to latest before pasting, so Enter then submits.
        fake = FakeDesktop(screens=[idle, idle, scrolled, working])
        await self.desktop(fake).tell("codex", "check the build")
        self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", "Enter"), ("-t", "=maslow-codex:", "Enter")])
        # Enter became a newline: the words are still in the input box, so submit again.
        stuck = "› check whether example.com is reachable\n  ? for shortcuts"
        fake = FakeDesktop(screens=[idle, idle, idle, stuck, "• Working (1s • esc to interrupt)"])
        await self.desktop(fake).tell("codex", "check whether example.com is reachable")
        self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", "Enter"), ("-t", "=maslow-codex:", "Enter")])
        # Codex still starting its tools: Tab queues the message.
        fake = FakeDesktop(screens=[idle, idle, idle, "› check\n  tab to queue message", "• Working (1s • esc to interrupt)"])
        await self.desktop(fake).tell("codex", "check")
        self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", "Enter"), ("-t", "=maslow-codex:", "Tab")])

    async def test_words_swallowed_during_startup_are_pasted_again_or_reported(self):
        fake = FakeDesktop(drops=1)
        self.assertEqual((await self.desktop(fake).tell("codex", "find cheap flights"))["status"], "sent")
        self.assertEqual(fake.pasted(), ["find cheap flights", "find cheap flights"])
        self.assertEqual(fake.submitted, ["find cheap flights"])
        fake = FakeDesktop(drops=2)
        with self.assertRaises(VoiceError) as raised:
            await self.desktop(fake).tell("codex", "find cheap flights")
        self.assertEqual(raised.exception.code, "NOT_DELIVERED")

    async def test_nothing_is_pasted_before_the_input_box_is_drawn(self):
        fake = FakeDesktop(screen="  Booting MCP server: playwright")
        with self.assertRaises(VoiceError) as raised:
            await self.desktop(fake).tell("codex", "hello")
        self.assertEqual(raised.exception.code, "AGENT_NOT_READY")
        self.assertEqual(fake.pasted(), [])

    async def test_no_key_is_pressed_once_a_decision_appears_after_submitting(self):
        dialog = '› check\n  Allow the playwright MCP server to run tool "browser_navigate"?\n  › 1. Allow\n  ? for shortcuts'
        ready = "› Ask Codex\n  ? for shortcuts"
        fake = FakeDesktop(screens=[ready, ready, ready, dialog, dialog])
        await self.desktop(fake).tell("codex", "check")
        self.assertEqual(fake.keys(), [("-t", "=maslow-codex:", "Enter")])

    async def test_tool_dialogs_codex_would_remember_are_answered_in_the_window(self):
        dialog = 'Allow the playwright MCP server to run tool "browser_navigate"?\n  url: https://example.com\n  › 1. Allow\n    3. Always allow'
        fake = FakeDesktop(screen=dialog)
        self.assertIn("browser_navigate", (await self.desktop(fake).tell("codex", "next"))["prompt"])
        with self.assertRaises(VoiceError) as raised:
            await self.desktop(fake).tell("codex", "", "approve")
        self.assertEqual(raised.exception.code, "ANSWER_IN_WINDOW")
        self.assertEqual(fake.keys(), [])

    async def test_window_of_an_ended_session_is_replaced_not_focused(self):
        fake = FakeDesktop()
        fake.windows.append({"address": "0x5", "class": "maslow.voice.codex", "mapped": True})
        original = fake.run
        async def run(*args):
            if "has-session" in args:
                raise VoiceError("DESKTOP_FAILED", "no session")
            return await original(*args)
        await DesktopActions(run, timeout=0.5, agent_cwd=Path(self.temp.name) / "Maslow Voice").open("codex")
        self.assertTrue(any(call[0] == "setsid" for call in fake.calls))

    async def test_agent_state_reads_working_waiting_idle_and_closed(self):
        for screen, expected in (("• Working (3s • esc to interrupt)", "working"), (APPROVAL, "waiting"), ("• Done.\n› Ask Codex", "idle")):
            fake = FakeDesktop(screen=screen)
            self.assertEqual((await self.desktop(fake).agent_state("codex"))["state"], expected)
        async def gone(*args):
            raise VoiceError("DESKTOP_FAILED", "no session")
        self.assertEqual((await DesktopActions(gone).agent_state("codex"))["state"], "closed")
        with self.assertRaises(VoiceError):
            await DesktopActions(gone).agent_state("bash")

    async def test_answer_without_a_waiting_prompt_sends_nothing(self):
        fake = FakeDesktop()
        with self.assertRaisesRegex(VoiceError, "not waiting"):
            await self.desktop(fake).tell("codex", "", "approve")
        self.assertEqual(fake.keys(), [])

    async def test_agent_that_never_becomes_ready_gets_no_keys(self):
        fake = FakeDesktop(states=["0|bash"])
        with self.assertRaises(VoiceError) as raised:
            await self.desktop(fake).tell("codex", "hello")
        self.assertEqual(raised.exception.code, "AGENT_NOT_READY")
        self.assertEqual(fake.keys(), [])

    async def test_unknown_agent_or_answer_is_rejected_before_any_command(self):
        fake = FakeDesktop()
        desktop = self.desktop(fake)
        for agent, reply in (("bash", ""), ("terminal", ""), ("codex", "always"), ("codex", "1"), ("claude", "2")):
            with self.assertRaises(VoiceError):
                await desktop.tell(agent, "hello", reply)
        self.assertEqual(fake.calls, [])

    async def test_missing_tmux_fails_before_launch(self):
        fake = FakeDesktop()
        with patch("maslow_voice.desktop.shutil.which", side_effect=lambda name: None if name == "tmux" else "/usr/bin/codex"):
            with self.assertRaisesRegex(VoiceError, "tmux"):
                await self.desktop(fake).open("codex")
        self.assertEqual(fake.calls, [])

    async def test_redirected_agent_folder_is_refused(self):
        real = Path(self.temp.name) / "real"
        real.mkdir()
        link = Path(self.temp.name) / "link"
        link.symlink_to(real)
        fake = FakeDesktop()
        with self.assertRaises(VoiceError):
            await DesktopActions(fake.run, timeout=0.5, agent_cwd=link / "Maslow Voice").open("codex")
        self.assertFalse(any(call[0] == "setsid" for call in fake.calls))


if __name__ == "__main__":
    unittest.main()
