import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from maslow_voice.errors import VoiceError
from maslow_voice.workspaces import WorkspaceResolver


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Mock()
        self.store.list.return_value = []
        self.resolver = WorkspaceResolver(self.root / "state", self.store, self.root / "projects")

    def test_auto_and_duplicate_survive_restart(self):
        first = self.resolver.resolve("turn-one", "Make a tracker")
        again = WorkspaceResolver(self.root / "state", self.store, self.root / "projects")
        self.assertEqual(again.resolve("turn-one", "Different title", new=True), first)
        self.assertTrue(Path(first).is_dir())
        self.assertEqual(len(list((self.root / "projects").iterdir())), 1)

    def test_existing_selection_and_explicit_new(self):
        selected = self.root / "existing"
        selected.mkdir()
        self.assertEqual(self.resolver.resolve("one", "Task", selected=str(selected)), str(selected))
        created = self.resolver.resolve("two", "Task", selected=str(selected), name="Fresh", new=True)
        self.assertNotEqual(created, str(selected))
        self.assertTrue(Path(created).name.startswith("fresh-"))

    def test_named_projects_and_ambiguity(self):
        for parent in ("a", "b"):
            (self.root / parent / "demo").mkdir(parents=True)
        self.store.list.return_value = [{"project": str(self.root / "a/demo")}]
        self.assertEqual(self.resolver.resolve("one", "Task", name="DEMO"), str(self.root / "a/demo"))
        self.store.list.return_value.append({"project": str(self.root / "b/demo")})
        with self.assertRaisesRegex(VoiceError, "Several projects"):
            self.resolver.resolve("two", "Task", name="demo")
        with self.assertRaisesRegex(VoiceError, "No saved Voice project"):
            self.resolver.resolve("three", "Task", name="unknown")

    def test_no_symlink_redirect_or_path_name(self):
        target = self.root / "other"
        target.mkdir()
        self.resolver.root.symlink_to(target)
        with self.assertRaisesRegex(VoiceError, "symbolic"):
            self.resolver.resolve("one", "Task")
        with self.assertRaises(VoiceError):
            self.resolver.resolve("two", "Task", name="../../outside", new=True)
        self.assertEqual(list(target.iterdir()), [])

    def test_collision_preserves_existing_content(self):
        import hashlib
        base = self.resolver.root / ("task-" + hashlib.sha256(b"one").hexdigest()[:10])
        base.mkdir(parents=True)
        marker = base / "keep.txt"
        marker.write_text("keep")
        self.assertNotEqual(self.resolver.resolve("one", "Task"), str(base))
        self.assertEqual(marker.read_text(), "keep")

    def test_new_named_project_can_be_resolved_by_spoken_name(self):
        project = self.resolver.resolve("one", "Build something", name="Client Portal", new=True)
        self.assertEqual(self.resolver.resolve("two", "Fix it", name="client portal"), project)
