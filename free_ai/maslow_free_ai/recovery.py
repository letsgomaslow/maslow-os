"""Stopped-router snapshots. Secrets remain in Secret Service, never in receipts.

This is the user-owned half of recovery. A snapshot is not installation approval
or proof of a compatible executable downgrade; privileged package delivery must
verify its own signed artifacts and pair them with this receipt.
"""

import asyncio
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

from .errors import FreeAIError
from .state import atomic_json, private_directory

MAX_DATABASE = 128 * 1024 * 1024
SNAPSHOT_ID = re.compile(r"[a-f0-9]{32}")
VERIFY_KEY = r"""
const crypto = require('node:crypto');
let data = ''; process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { data += chunk; if(data.length > 16384) process.exit(1); });
process.stdin.on('end', () => { try {
  const {key, rows} = JSON.parse(data);
  if(!/^[a-f0-9]{64}$/.test(key) || rows.length !== 1) throw Error();
  for(const row of rows) {
    if(row.platform !== 'groq' || !/^[a-f0-9]+$/i.test(row.encrypted_key) || !/^[a-f0-9]{24}$/i.test(row.iv) || !/^[a-f0-9]{32}$/i.test(row.auth_tag)) throw Error();
    const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(key, 'hex'), Buffer.from(row.iv,'hex'), {authTagLength:16});
    decipher.setAuthTag(Buffer.from(row.auth_tag,'hex'));
    const clear = decipher.update(row.encrypted_key,'hex','utf8') + decipher.final('utf8');
    if(!/^gsk_[A-Za-z0-9_-]{16,256}$/.test(clear)) throw Error();
  }
  process.stdout.write('MATCH\n');
} catch { process.exit(1); } });
"""


def fingerprint(key):
    if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
        raise FreeAIError("RECOVERY_KEY_UNAVAILABLE", "The matching recovery key is unavailable. No files were changed.")
    return hashlib.sha256(bytes.fromhex(key)).hexdigest()


def checked_file(path, limit=MAX_DATABASE):
    """Reject symlinks, aliases, public files and unbounded input before opening."""
    path = Path(path)
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise FreeAIError("UNSAFE_RECOVERY", "Recovery files must be private and unaliased.")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > limit:
        raise FreeAIError("UNSAFE_RECOVERY", "Recovery files must be private, bounded and unaliased.")
    return info


def file_hash(path):
    before = checked_file(path)
    with Path(path).open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise FreeAIError("RECOVERY_CHANGED", "Recovery files changed during verification.")
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = checked_file(path)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise FreeAIError("RECOVERY_CHANGED", "Recovery files changed during verification.")
    return value


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backup_database(source, target):
    checked_file(source)
    for name in (str(source) + '-wal', str(source) + '-shm'):
        if Path(name).exists() or Path(name).is_symlink():
            checked_file(name)
    # Exclusive target creation prevents retry from adopting an old snapshot.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    deadline = time.monotonic() + 20
    def progress(*_):
        if time.monotonic() > deadline:
            raise TimeoutError()
    try:
        with closing(sqlite3.connect(Path(source).as_uri() + '?mode=ro', uri=True, timeout=1)) as source_db, closing(sqlite3.connect(target)) as destination:
            source_db.backup(destination, pages=256, progress=progress, sleep=0.05)
            if destination.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError()
        checked_file(source)
        checked_file(target)
        with Path(target).open('rb') as stream:
            os.fsync(stream.fileno())
    except BaseException:
        Path(target).unlink(missing_ok=True)
        raise


class Recovery:
    def __init__(self, state, keys, node):
        self.state, self.keys, self.node = state, keys, Path(node)
        self.root = private_directory(state.directory / 'recovery')
        self.marker = state.directory / 'maintenance.json'

    def pending(self):
        return self.marker.exists() or self.marker.is_symlink()

    async def verify_key(self, database, key):
        fingerprint(key)
        checked_file(database)
        try:
            with closing(sqlite3.connect(Path(database).as_uri() + '?mode=ro', uri=True)) as db:
                rows = [dict(zip(('platform','encrypted_key','iv','auth_tag'), row)) for row in db.execute('SELECT platform,encrypted_key,iv,auth_tag FROM api_keys')]
            payload = json.dumps({'key':key,'rows':rows}).encode()
            if len(payload) > 16384:
                raise ValueError()
            process = await asyncio.create_subprocess_exec(str(self.node), '--eval', VERIFY_KEY,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                env={'PATH':'/usr/bin:/bin'}, cwd=str(self.root))
            try:
                output, _ = await asyncio.wait_for(process.communicate(payload), 10)
            except BaseException:
                if process.returncode is None:
                    process.kill()
                await process.wait()
                raise
            if process.returncode or output != b'MATCH\n':
                raise ValueError()
        except (OSError, ValueError, sqlite3.Error, TimeoutError):
            raise FreeAIError('RECOVERY_KEY_MISMATCH', 'The database and encryption key do not match. Package changes are blocked.') from None

    @staticmethod
    def validate_artifacts(artifacts):
        if not isinstance(artifacts, dict) or not artifacts or any(name not in {'maslow-free-ai','maslow-voice'} or not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{64}', value) for name,value in artifacts.items()):
            raise FreeAIError('RECOVERY_ARTIFACT_REQUIRED', 'Recovery needs exact verified package identities.')

    async def snapshot(self, database, *, artifacts):
        """Admission/shutdown are the caller's locked preconditions.

        A durable marker is written first. Failure deliberately leaves admission
        closed; explicit abandon is needed after inspecting the failure.
        """
        if self.pending():
            raise FreeAIError('RECOVERY_PENDING', 'Finish or abandon the pending recovery operation first.')
        self.validate_artifacts(artifacts)
        identity = uuid.uuid4().hex
        atomic_json(self.marker, {'schema':1,'id':identity,'state':'preparing'})
        directory = self.root / identity
        directory.mkdir(mode=0o700)
        try:
            database = Path(database)
            if not database.exists() and not database.is_symlink():
                if self.state.value['configured']:
                    raise FreeAIError('RECOVERY_DATABASE_MISSING', 'The configured router database is missing. Restore it before package changes.')
                key = await self.keys.get()  # Locked/unavailable keyring is not fresh state.
                if key is not None:
                    raise FreeAIError('RECOVERY_STATE_MISMATCH', 'An existing encryption key needs its matching database before package changes.')
                receipt = {'schema':1,'id':identity,'kind':'fresh','database_sha256':None,'key_fingerprint':None,'artifacts':artifacts}
            else:
                key = await self.keys.get()
                if key is None:
                    raise FreeAIError('RECOVERY_KEY_UNAVAILABLE', 'The matching encryption key is missing. Package changes are blocked.')
                destination = directory / 'router.sqlite3'
                await asyncio.to_thread(backup_database, database, destination)
                await self.verify_key(destination, key)
                await self.keys.save_recovery(identity, key)
                if await self.keys.get_recovery(identity) != key:
                    raise FreeAIError('RECOVERY_KEY_UNAVAILABLE', 'The recovery key could not be retained in Secret Service.')
                receipt = {'schema':1,'id':identity,'kind':'snapshot','database_sha256':file_hash(destination),'key_fingerprint':fingerprint(key),'artifacts':artifacts}
            atomic_json(directory / 'settings.json', self.state.value)
            receipt['settings_sha256'] = file_hash(directory / 'settings.json')
            atomic_json(directory / 'receipt.json', receipt)
            sync_directory(directory)
            atomic_json(self.marker, {'schema':1,'id':identity,'state':'prepared'})
            return receipt
        except asyncio.CancelledError:
            raise
        except FreeAIError:
            raise
        except (OSError, sqlite3.Error, ValueError, TimeoutError):
            raise FreeAIError('RECOVERY_SNAPSHOT_FAILED', 'A consistent recovery snapshot could not be saved. Package changes are blocked.') from None

    async def verify(self, identity, *, artifacts):
        if not isinstance(identity,str) or not SNAPSHOT_ID.fullmatch(identity):
            raise FreeAIError('INVALID_RECOVERY', 'Choose a recorded recovery snapshot.')
        directory = self.root / identity
        try:
            checked_file(directory / 'receipt.json', 8192)
            receipt = json.loads((directory / 'receipt.json').read_text())
            if set(receipt) != {'schema','id','kind','database_sha256','key_fingerprint','artifacts','settings_sha256'} or receipt['schema'] != 1 or receipt['id'] != identity or receipt['artifacts'] != artifacts:
                raise ValueError()
            if file_hash(directory / 'settings.json') != receipt['settings_sha256']:
                raise ValueError()
            if receipt['kind'] == 'snapshot':
                database = directory / 'router.sqlite3'
                if file_hash(database) != receipt['database_sha256']:
                    raise ValueError()
                key = await self.keys.get_recovery(identity)
                if fingerprint(key) != receipt['key_fingerprint']:
                    raise ValueError()
                await self.verify_key(database,key)
            elif receipt['kind'] != 'fresh' or receipt['database_sha256'] is not None or receipt['key_fingerprint'] is not None or (directory / 'router.sqlite3').exists():
                raise ValueError()
            return receipt
        except FreeAIError:
            raise
        except (OSError,ValueError,TypeError,KeyError):
            raise FreeAIError('RECOVERY_INVALID', 'The recovery snapshot or package pairing is invalid. No files were changed.') from None

    async def restore_prepared(self, identity, *, artifacts):
        """Restore only the current quiesced operation after package pairing.

        Historical rollback after admission resumed is deliberately unavailable:
        replaying an older database could reset quota or resurrect retired routes.
        The privileged installer must independently verify the exact retained
        package hashes before calling this user-owned operation.
        """
        try:
            checked_file(self.marker, 4096)
            marker = json.loads(self.marker.read_text())
            if marker != {"schema": 1, "id": identity, "state": "prepared"}:
                raise ValueError()
        except (OSError, ValueError, TypeError):
            raise FreeAIError("RECOVERY_NOT_PREPARED", "Only the current stopped recovery operation can be restored.") from None
        receipt = await self.verify(identity, artifacts=artifacts)
        if receipt["kind"] != "snapshot":
            raise FreeAIError("RECOVERY_NO_DATABASE", "This fresh-install record has no earlier router database to restore.")
        key = await self.keys.get_recovery(identity)
        current = await self.keys.get()
        if current is not None and fingerprint(current) != receipt["key_fingerprint"]:
            raise FreeAIError("RECOVERY_KEY_CHANGED", "The current encryption key changed. It was not overwritten; inspect the retained snapshot before continuing.")
        source = self.root / identity / "router.sqlite3"
        target = self.state.directory / "router.sqlite3"
        replacement = self.state.directory / (".restore-" + identity)
        try:
            if target.exists() or target.is_symlink():
                checked_file(target)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(target) + suffix)
                if sidecar.exists() or sidecar.is_symlink():
                    checked_file(sidecar)
            await asyncio.to_thread(backup_database, source, replacement)
            await self.verify_key(replacement, key)
            if current is None:
                await self.keys.create(key)
            if await self.keys.get() != key:
                raise FreeAIError("RECOVERY_KEY_CHANGED", "The active key does not match the snapshot. Admission stays closed.")
            # Keep the marker through every replacement/failure. A crash here
            # cannot start the router against a partially restored pair.
            for suffix in ("-wal", "-shm"):
                Path(str(target) + suffix).unlink(missing_ok=True)
            os.replace(replacement, target)
            sync_directory(self.state.directory)
            # Use current user confirmation/settings; never restore old enables.
            self.state.update(enabled=False, verified_routes=[])
            return {"schema": 1, "id": identity, "restored": True,
                    "database_sha256": file_hash(target), "connection_check_required": True}
        except FreeAIError:
            raise
        except (OSError, sqlite3.Error, ValueError, TimeoutError):
            raise FreeAIError("RECOVERY_RESTORE_FAILED", "Recovery could not finish. Admission remains closed and the snapshot was retained.") from None
        finally:
            replacement.unlink(missing_ok=True)

    def abandon(self):
        """Close a failed/prepared operation, retaining snapshots for diagnosis.

        This never installs a package or restores credentials and forces a fresh
        connection check before admitting managed assistant work.
        """
        self.state.update(enabled=False, verified_routes=[])
        if self.marker.is_symlink():
            raise FreeAIError('UNSAFE_RECOVERY','The maintenance marker needs repair.')
        self.marker.unlink(missing_ok=True)
        sync_directory(self.state.directory)
