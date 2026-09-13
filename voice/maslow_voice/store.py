"""Task state outlives voice sessions and upstream ephemeral event streams."""

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

from .config import private_directory
from .errors import VoiceError

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}
STATES = TERMINAL | {"queued", "submitting", "accepted", "running", "waiting_input", "awaiting_approval", "stopping"}


class TaskStore:
    def __init__(self, directory):
        self.path = private_directory(Path(directory)) / "tasks.sqlite3"
        if self.path.is_symlink():
            raise VoiceError("UNSAFE_STATE", "Task storage must not be a symbolic link.")
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL,
                state TEXT NOT NULL, data TEXT NOT NULL, updated_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                kind TEXT NOT NULL, data TEXT NOT NULL, created_at REAL NOT NULL);
            PRAGMA user_version=1;
        """)

    def create(self, request_id, brief, project, mode, source):
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise VoiceError("INVALID_REQUEST", "The task request has no valid identity.")
        payload = {"brief": brief, "project": project, "mode": mode, "source": source}
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT * FROM tasks WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise VoiceError("REQUEST_CONFLICT", "This request identity already belongs to a different task.")
                self.db.execute("COMMIT")
                return json.loads(old["data"]), False
            task_id = str(uuid.uuid4())
            now = time.time()
            data = dict(payload, id=task_id, request_id=request_id, title=brief["objective"][:160], summary=brief["summary"],
                        state="queued", run_id=None, session_id=None, owner="Hermes", children=[], result="", error=None,
                        approval=None, dismissed=False, created_at=now, updated_at=now, attempt=0)
            self.db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?)", (task_id, request_id, fingerprint, "queued", json.dumps(data), now))
            self._event(task_id, "queued", {"state": "queued"})
            self.db.execute("COMMIT")
            return data, True
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def _event(self, task_id, kind, data):
        self.db.execute("INSERT INTO events(task_id,kind,data,created_at) VALUES (?,?,?,?)", (task_id, kind, json.dumps(data), time.time()))

    def get(self, task_id):
        row = self.db.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise VoiceError("TASK_NOT_FOUND", "That task is no longer in Voice history.")
        return json.loads(row["data"])

    def update(self, task_id, *, event="updated", **changes):
        task = self.get(task_id)
        if "state" in changes and changes["state"] not in STATES:
            raise VoiceError("INVALID_TASK_STATE", "The executor returned an unsupported task state.")
        if {"id", "request_id", "mode", "source", "project"} & changes.keys():
            raise VoiceError("IMMUTABLE_TASK", "A task's identity and execution boundary cannot be changed.")
        task.update(changes, updated_at=time.time())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("UPDATE tasks SET state=?,data=?,updated_at=? WHERE id=?", (task["state"], json.dumps(task), task["updated_at"], task_id))
            self._event(task_id, event, changes)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return task

    def list(self, limit=100):
        return [json.loads(row[0]) for row in self.db.execute("SELECT data FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,))]

    def active(self):
        return [task for task in self.list(10000) if task["state"] not in TERMINAL]

    def events(self, task_id, after=0):
        self.get(task_id)
        return [dict(row, data=json.loads(row["data"])) for row in self.db.execute("SELECT * FROM events WHERE task_id=? AND seq>? ORDER BY seq LIMIT 1000", (task_id, after))]

    def prune(self, days=30):
        cutoff = time.time() - days * 86400
        self.db.execute("DELETE FROM tasks WHERE updated_at<? AND state IN ('completed','failed','cancelled')", (cutoff,))

    def close(self):
        self.db.close()
