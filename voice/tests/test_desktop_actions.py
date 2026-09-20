import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from maslow_voice.desktop import DesktopActions
from maslow_voice.errors import VoiceError


class DesktopTests(unittest.IsolatedAsyncioTestCase):
    async def test_launch_then_refocus_observed_codex(self):
        clients = []
        calls = []
        async def run(*args):
            calls.append(args)
            if args[:3] == ("hyprctl", "-j", "clients"):
                return json.dumps(clients)
            if args[0] == "setsid":
                clients.append({"address": "0x123", "class": "maslow.voice.codex", "mapped": True})
            return "ok"
        desktop = DesktopActions(run)
        with patch("maslow_voice.desktop.shutil.which", return_value="/bin/codex"):
            self.assertEqual((await desktop.open("codex"))["status"], "opened")
            self.assertEqual((await desktop.open("codex"))["status"], "focused")
        launches = [call for call in calls if call[0] == "setsid"]
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0][-2:], ("--", "codex"))
        self.assertEqual(sum(c[:3] == ("hyprctl", "dispatch", "focuswindow") for c in calls), 2)

    async def test_unobserved_launch_is_not_success(self):
        desktop = DesktopActions(AsyncMock(return_value="[]"), timeout=0)
        with self.assertRaisesRegex(VoiceError, "window did not appear"):
            await desktop.open("terminal")

    async def test_invalid_target_and_missing_codex_launch_nothing(self):
        runner = AsyncMock()
        desktop = DesktopActions(runner)
        for target in ("terminal; id", "codex --yolo", "unknown", None):
            with self.assertRaises(VoiceError):
                await desktop.open(target)
        with patch("maslow_voice.desktop.shutil.which", return_value=None):
            with self.assertRaisesRegex(VoiceError, "Hub setup"):
                await desktop.open("codex")
        runner.assert_not_awaited()

    async def test_hub_ack_is_not_window_claim(self):
        runner = AsyncMock(return_value="ok")
        receipt = await DesktopActions(runner).open("hub")
        self.assertEqual(receipt["verification"], "shell_acknowledged")
        runner.assert_awaited_once_with("omarchy-launch-hub", "setup")

    async def test_artifact_open_rechecks_file_and_containment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "index.html").write_text("<h1>Result</h1>")
            (root / "secret").write_text("private")
            (project / "escape").symlink_to(root / "secret")
            task = {"project": str(project), "artifacts": [{"path": "index.html"}, {"path": "escape"}]}
            runner = AsyncMock(return_value="")
            desktop = DesktopActions(runner)
            await desktop.open_path(task, "index.html")
            self.assertEqual(runner.call_args.args[-1], (project / "index.html").as_uri())
            for path in ("escape", "../secret", "/etc/passwd", "unknown"):
                with self.assertRaises(VoiceError):
                    await desktop.open_path(task, path)
            (project / "index.html").unlink()
            with self.assertRaises(VoiceError):
                await desktop.open_path(task, "index.html")
            self.assertEqual(runner.await_count, 1)
