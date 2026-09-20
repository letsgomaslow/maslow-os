"""Resolve explicit Voice work without making a folder a conversation prerequisite."""

import hashlib
import json
import re
from pathlib import Path

from .config import atomic_json
from .errors import VoiceError


class WorkspaceResolver:
    def __init__(self, directory, store, root=None):
        self.path = Path(directory) / "workspaces.json"
        self.root = Path(root) if root is not None else Path.home() / "Projects" / "Maslow Voice"
        self.store = store
        if self.path.is_symlink():
            raise VoiceError("UNSAFE_STATE", "Voice workspace records must not be a symbolic link.")
        self.assignments = json.loads(self.path.read_text()) if self.path.exists() else {}

    @staticmethod
    def existing(value):
        path = Path(value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            raise VoiceError("PROJECT_REQUIRED", "Choose an existing project folder.")
        return str(path.resolve())

    def resolve(self, request_id, title, *, selected="", name="", new=False):
        if request_id in self.assignments:
            saved = self.assignments[request_id]
            return self.existing(saved["path"] if isinstance(saved, dict) else saved)
        if not isinstance(name, str) or len(name) > 120 or any(ord(c) < 32 for c in name) or "/" in name or "\\" in name or name in {".", ".."}:
            raise VoiceError("INVALID_PROJECT", "Use a project name, or choose a folder in Voice.")
        name = name.strip()
        if name and not new:
            known = {task["project"]: {Path(task["project"]).name.casefold()} for task in self.store.list(10000)}
            for saved in self.assignments.values():
                path = saved["path"] if isinstance(saved, dict) else saved
                known.setdefault(path, {Path(path).name.casefold()}).add(str(saved.get("name", "") if isinstance(saved, dict) else "").casefold())
            matches = sorted(path for path, names in known.items() if name.casefold() in names and Path(path).is_dir())
            if len(matches) > 1:
                raise VoiceError("PROJECT_AMBIGUOUS", "Several projects have that name. Choose the intended folder in Voice.")
            if not matches:
                raise VoiceError("PROJECT_NOT_FOUND", "No saved Voice project has that name. Choose its folder or ask for a new project.")
            project = self.existing(matches[0])
        elif selected and not new:
            project = self.existing(selected)
        else:
            # Refuse redirects anywhere in the managed root. Never overwrite an
            # existing directory, including a leftover from a failed allocation.
            if any(parent.is_symlink() for parent in (self.root, *self.root.parents)):
                raise VoiceError("UNSAFE_PROJECT", "The managed Voice project folder cannot use symbolic links.")
            self.root.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", (name or title).lower()).strip("-")[:48] or "project"
            suffix = hashlib.sha256(request_id.encode()).hexdigest()[:10]
            base = self.root / f"{slug}-{suffix}"
            candidate = base
            for index in range(1000):
                try:
                    candidate.mkdir(mode=0o700)
                    break
                except FileExistsError:
                    candidate = self.root / f"{base.name}-{index + 1}"
            else:
                raise VoiceError("PROJECT_UNAVAILABLE", "Could not allocate a new project folder.")
            project = str(candidate.resolve())
        self.assignments[request_id] = {"path": project, "name": name or Path(project).name}
        atomic_json(self.path, self.assignments)
        return project
