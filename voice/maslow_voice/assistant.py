"""Explicit everyday-assistant grants and descriptor-based workspace operations.

No model-supplied path can enlarge the grant. Connected-account capabilities
remain unavailable until Connect supplies the reviewed managed-session contract.
"""

import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .errors import VoiceError

POLICY_REVISION = "maslow-everyday-1"
MAX_DOCUMENT = 128 * 1024
MAX_NOTE = 64 * 1024
MAX_DOCUMENTS = 32


def relative_document(value, *, note=False):
    if not isinstance(value, str) or not value or len(value) > 240 or any(ord(c) < 32 for c in value) or "\\" in value:
        raise VoiceError("INVALID_DOCUMENT", "Choose a plain relative document path in the workspace.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {".", "..", ""} for part in value.split("/")):
        raise VoiceError("INVALID_DOCUMENT", "Document paths must stay inside the selected workspace.")
    if path.suffix.lower() not in ({".md"} if note else {".md", ".txt"}):
        raise VoiceError("INVALID_DOCUMENT", "Choose a Markdown note." if note else "Choose a Markdown or text document.")
    return value


def _identity(info):
    return {"device": info.st_dev, "inode": info.st_ino}


def _text(data):
    try:
        text = data.decode("utf-8")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            raise ValueError()
        return text
    except (UnicodeError, ValueError):
        raise VoiceError("INVALID_DOCUMENT", "Only UTF-8 text documents can be read or saved.") from None


@contextmanager
def _directory(path):
    """Walk from / using O_NOFOLLOW; no symlink traversal or stat/open gap."""
    path = Path(path)
    if not path.is_absolute():
        raise VoiceError("PROJECT_REQUIRED", "Choose an existing workspace folder.")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd
    except OSError:
        raise VoiceError("UNSAFE_WORKSPACE", "The workspace or one of its folders changed or uses a symbolic link.") from None
    finally:
        os.close(fd)


@contextmanager
def _parent(root_fd, relative):
    fd = os.dup(root_fd)
    parts = relative.split("/")
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = new
        yield fd, parts[-1]
    except OSError:
        raise VoiceError("UNSAFE_DOCUMENT", "The document folder changed or uses a symbolic link.") from None
    finally:
        os.close(fd)


def _read(root_fd, relative, expected=None, *, maximum=MAX_DOCUMENT):
    with _parent(root_fd, relative) as (parent, name):
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        except OSError:
            raise VoiceError("UNSAFE_DOCUMENT", "The selected document is unavailable or uses a symbolic link.") from None
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (expected and _identity(info) != expected):
                raise VoiceError("UNSAFE_DOCUMENT", "The selected document changed, is linked, or is not a regular file.")
            if info.st_size > maximum:
                raise VoiceError("DOCUMENT_TOO_LARGE", "The selected document exceeds the preview's text limit.")
            chunks, size = [], 0
            while chunk := os.read(fd, min(8192, maximum + 1 - size)):
                chunks.append(chunk)
                size += len(chunk)
                if size > maximum:
                    raise VoiceError("DOCUMENT_TOO_LARGE", "The selected document exceeds the preview's text limit.")
            after = os.fstat(fd)
            if (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink):
                raise VoiceError("DOCUMENT_CHANGED", "The document changed while it was being read. Select it again.")
            data = b"".join(chunks)
            _text(data)
            return data, _identity(info)
        finally:
            os.close(fd)


def grant_workspace(project, capabilities, *, accounts_verified=False):
    if not isinstance(capabilities, dict) or set(capabilities) - {"documents", "note", "accounts"}:
        raise VoiceError("INVALID_CAPABILITIES", "Choose the files and accounts for this request.")
    documents, note, accounts = capabilities.get("documents", []), capabilities.get("note"), capabilities.get("accounts", [])
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS:
        raise VoiceError("INVALID_CAPABILITIES", "Select at most 32 text documents.")
    names = [relative_document(item) for item in documents]
    if len(set(names)) != len(names):
        raise VoiceError("INVALID_CAPABILITIES", "Select each document only once.")
    if not isinstance(accounts, list) or (accounts and not accounts_verified):
        raise VoiceError("MANAGED_ACCOUNTS_UNAVAILABLE", "Scoped account access is awaiting an accepted Connect package. No account was accessed.")
    if note is not None:
        note = relative_document(note, note=True)
    # resolve() would follow a user-unselected symlink. Reject such paths instead.
    if not isinstance(project, str) or not project or "\x00" in project:
        raise VoiceError("PROJECT_REQUIRED", "Choose an existing workspace folder.")
    expanded = Path(os.path.expanduser(project))
    if not expanded.is_absolute():
        raise VoiceError("PROJECT_REQUIRED", "Choose an existing workspace using its full folder path.")
    path = Path(os.path.abspath(expanded))
    with _directory(path) as root:
        files = {}
        for name in sorted(names):
            _, identity = _read(root, name)
            files[name] = identity
        if note:
            with _parent(root, note) as (parent, name):
                try:
                    os.stat(name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise VoiceError("NOTE_EXISTS", "Choose a new note name. Existing files are never overwritten.")
        return str(path), {"workspace_identity": _identity(os.fstat(root)), "documents": files, "note": note, "accounts": list(accounts)}


class WorkspaceTools:
    def __init__(self, store):
        self.store = store

    def verify_requested_note(self, task):
        grant = task["granted_capabilities"]
        if not grant["note"]:
            return
        saved = task.get("note_receipt") or {}
        if saved.get("state") != "created" or saved.get("path") != grant["note"] or not saved.get("identity"):
            raise VoiceError("NOTE_NOT_CREATED", "The assistant finished without the requested checked note. Review its report before continuing.")
        with _directory(task["project"]) as root:
            if _identity(os.fstat(root)) != grant["workspace_identity"]:
                raise VoiceError("WORKSPACE_CHANGED", "The workspace changed before completion. Review the saved note.")
            data, _ = _read(root, grant["note"], saved["identity"], maximum=MAX_NOTE)
            if len(data) != saved["size"] or hashlib.sha256(data).hexdigest() != saved["sha256"]:
                raise VoiceError("NOTE_CHANGED", "The saved note changed before completion. Review it before using the result.")

    async def handle(self, task, operation, params):
        if task.get("execution_connection") != "free-cloud" or task.get("policy_revision") != POLICY_REVISION:
            raise VoiceError("INVALID_ASSISTANT_POLICY", "This task does not have the reviewed assistant permissions.")
        fields = {"list_documents": set(), "read_document": {"path"}, "create_note": {"path", "content"}}
        if operation not in fields or not isinstance(params, dict) or set(params) != fields[operation]:
            raise VoiceError("INVALID_TOOL", "That assistant operation or argument is unavailable.")
        grant = task["granted_capabilities"]
        with _directory(task["project"]) as root:
            if _identity(os.fstat(root)) != grant["workspace_identity"]:
                raise VoiceError("WORKSPACE_CHANGED", "The workspace changed. Start a new request in the intended folder.")
            if operation == "list_documents":
                return {"documents": sorted(grant["documents"])}
            path = relative_document(params["path"], note=operation == "create_note")
            if operation == "read_document":
                if path not in grant["documents"]:
                    raise VoiceError("DOCUMENT_NOT_GRANTED", "The user did not select this document for the task.")
                data, _ = _read(root, path, grant["documents"][path])
                return {"path": path, "content": _text(data), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if path != grant["note"]:
                raise VoiceError("SAVE_NOT_GRANTED", "The user did not request saving this note.")
            content = params["content"]
            if not isinstance(content, str):
                raise VoiceError("INVALID_DOCUMENT", "A note must contain text.")
            data = content.encode("utf-8")
            if len(data) > MAX_NOTE:
                raise VoiceError("DOCUMENT_TOO_LARGE", "The note exceeds the preview's text limit.")
            _text(data)
            return self._create_note(task, root, path, data)

    def _create_note(self, task, root, path, data):
        digest = hashlib.sha256(data).hexdigest()
        saved = self.store.get(task["id"]).get("note_receipt")
        # Reserve content before creation. A crash can leave a partial note, but
        # never permits a replay to overwrite it or save different content.
        if saved and (saved["path"], saved["sha256"]) != (path, digest):
            raise VoiceError("NOTE_CONFLICT", "This task already reserved different note contents.")
        if saved:
            try:
                existing, _ = _read(root, path, saved.get("identity"), maximum=MAX_NOTE)
            except VoiceError:
                if saved["state"] == "created":
                    raise
            else:
                if not saved.get("identity"):
                    raise VoiceError("NOTE_INCOMPLETE", "The interrupted note creation cannot be attributed safely. Review it before a new request.")
                if existing != data:
                    raise VoiceError("NOTE_INCOMPLETE", "The reserved note is incomplete or changed. Review it and start a new request.")
                return self._receipt(task, path, data)
        else:
            self.store.update(task["id"], event="note_reserved", note_receipt={"path": path, "sha256": digest, "state": "reserved"})
        with _parent(root, path) as (parent, name):
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
            except FileExistsError:
                raise VoiceError("NOTE_EXISTS", "An existing file was left unchanged. Choose a new note name.") from None
            try:
                identity = _identity(os.fstat(fd))
                self.store.update(task["id"], event="note_opened", note_receipt={"path": path, "sha256": digest,
                    "state": "reserved", "identity": identity})
                remaining = memoryview(data)
                while remaining:
                    written = os.write(fd, remaining)
                    remaining = remaining[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(parent)
        checked, _ = _read(root, path, identity, maximum=MAX_NOTE)
        if checked != data:
            raise VoiceError("NOTE_CHANGED", "The note changed after saving. Review it before using the result.")
        return self._receipt(task, path, data)

    def _receipt(self, task, path, data):
        receipt = {"path": str(Path(task["project"]) / path), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        identity = self.store.get(task["id"]).get("note_receipt", {}).get("identity")
        artifact = {**receipt, "exists": True, "verification": "Bytes and SHA-256 checked; review generated facts."}
        self.store.update(task["id"], event="note_created", note_receipt={**receipt, "path": path, "state": "created", "identity": identity}, artifacts=[artifact])
        return receipt
