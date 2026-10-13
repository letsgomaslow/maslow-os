import asyncio
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from maslow_free_ai.credentials import EncryptionKey
from maslow_free_ai.errors import FreeAIError
from maslow_free_ai.recovery import Recovery, sync_directory
from maslow_free_ai.state import State

NODE = Path('/tmp/maslow-freellmapi-tools/node-v22.23.3-linux-x64/bin/node')
if not NODE.exists():
    NODE = Path(shutil.which('node') or '/nonexistent/node')
KEY = 'a' * 64
ENCRYPT = """const c=require('crypto');let k=Buffer.from('a'.repeat(64),'hex'),iv=c.randomBytes(16),e=c.createCipheriv('aes-256-gcm',k,iv);let s=e.update('gsk_'+ 'f'.repeat(32),'utf8','hex')+e.final('hex');process.stdout.write(JSON.stringify([s,iv.toString('hex'),e.getAuthTag().toString('hex')]));"""


@unittest.skipUnless(NODE.is_file(), 'Node crypto unavailable for actual ciphertext proof')
class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = State(Path(self.temp.name) / 'state')
        self.keys = Mock()
        self.keys.get = AsyncMock(return_value=KEY)
        self.keys.save_recovery = AsyncMock()
        self.keys.get_recovery = AsyncMock(return_value=KEY)
        self.recovery = Recovery(self.state, self.keys, NODE)
        self.database = self.state.directory / 'router.sqlite3'
        encrypted,iv,tag = json.loads(subprocess.check_output([str(NODE),'--eval',ENCRYPT]))
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute('CREATE TABLE api_keys(platform TEXT, encrypted_key TEXT, iv TEXT, auth_tag TEXT)')
            db.execute('INSERT INTO api_keys VALUES(?,?,?,?)',('groq',encrypted,iv,tag))
            db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
            db.execute('INSERT INTO settings VALUES(?,?)',('quota','7'))
        self.database.chmod(0o600)
        self.artifacts={'maslow-free-ai':'1'*64,'maslow-voice':'2'*64}

    def tearDown(self):
        self.temp.cleanup()

    async def test_installed_writer_16_byte_iv_verifies(self):
        # The pinned FreeLLMAPI writer uses randomBytes(16), not GCM's
        # commonly recommended 12-byte IV. Exercise its actual stored format.
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(len(db.execute('SELECT iv FROM api_keys').fetchone()[0]), 32)
        await self.recovery.verify_key(self.database, KEY)

    async def test_iv_format_and_authentication_tampering_are_rejected(self):
        with closing(sqlite3.connect(self.database)) as db:
            original_iv, original_tag = db.execute('SELECT iv,auth_tag FROM api_keys').fetchone()
        for iv, tag in [('a' * 24, original_tag), ('a' * 30, original_tag),
                        ('a' * 34, original_tag), ('z' * 32, original_tag),
                        (original_iv, ('0' if original_tag[0] != '0' else '1') + original_tag[1:])]:
            with self.subTest(iv_length=len(iv), malformed=iv.startswith('z')):
                with closing(sqlite3.connect(self.database)) as db, db:
                    db.execute('UPDATE api_keys SET iv=?,auth_tag=?', (iv, tag))
                with self.assertRaises(FreeAIError) as error:
                    await self.recovery.verify_key(self.database, KEY)
                self.assertEqual(error.exception.code, 'RECOVERY_KEY_MISMATCH')

    async def test_actual_sqlite_wal_snapshot_keeps_committed_quota_and_ciphertext(self):
        with closing(sqlite3.connect(self.database)) as active, active:
            active.execute('PRAGMA journal_mode=WAL')
            active.execute("UPDATE settings SET value='8' WHERE key='quota'")
            active.commit()
            for suffix in ('-wal','-shm'):
                Path(str(self.database)+suffix).chmod(0o600)
            receipt=await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        backup=self.recovery.root / receipt['id'] / 'router.sqlite3'
        with closing(sqlite3.connect(backup)) as db, db:
            self.assertEqual(db.execute("SELECT value FROM settings WHERE key='quota'").fetchone(),('8',))
        self.assertEqual(await self.recovery.verify(receipt['id'],artifacts=self.artifacts),receipt)
        self.keys.save_recovery.assert_awaited_once_with(receipt['id'],KEY)
        for file in (self.recovery.root / receipt['id']).iterdir():
            self.assertEqual(file.stat().st_mode & 0o777,0o600)
            self.assertNotIn(KEY.encode(),file.read_bytes())
            self.assertNotIn(b'gsk_'+b'f'*32,file.read_bytes())
        self.assertEqual(json.loads(self.recovery.marker.read_text())['state'],'prepared')

    async def test_wrong_key_and_locked_recovery_key_block_and_keep_admission_marker(self):
        self.keys.get.return_value='b'*64
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'RECOVERY_KEY_MISMATCH')
        self.keys.save_recovery.assert_not_called()
        self.assertTrue(self.recovery.pending())
        self.recovery.abandon()
        self.keys.get.return_value=KEY
        self.keys.save_recovery.side_effect=FreeAIError('KEYRING_LOCKED','locked')
        with self.assertRaises(FreeAIError):
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(json.loads(self.recovery.marker.read_text())['state'],'preparing')

    async def test_full_disk_backup_failure_never_returns_prepared_receipt(self):
        original=self.database.read_bytes()
        with patch('maslow_free_ai.recovery.backup_database',side_effect=OSError(28,'No space')):
            with self.assertRaises(FreeAIError) as error:
                await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'RECOVERY_SNAPSHOT_FAILED')
        self.assertEqual(original,self.database.read_bytes())
        self.assertTrue(self.recovery.pending())
        self.assertEqual(list(self.recovery.root.glob('*/receipt.json')),[])

    async def test_package_pairing_tamper_and_snapshot_tamper_denied(self):
        receipt=await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        with self.assertRaises(FreeAIError):
            await self.recovery.verify(receipt['id'],artifacts={'maslow-free-ai':'3'*64})
        backup=self.recovery.root / receipt['id'] / 'router.sqlite3'
        with closing(sqlite3.connect(backup)) as db, db:
            db.execute("UPDATE settings SET value='0'")
        with self.assertRaises(FreeAIError):
            await self.recovery.verify(receipt['id'],artifacts=self.artifacts)

    async def test_hardlink_and_symlink_inputs_are_not_backed_up(self):
        alias=self.database.with_name('alias')
        os.link(self.database,alias)
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'UNSAFE_RECOVERY')
        self.recovery.abandon();alias.unlink()
        original=self.database.with_name('original')
        self.database.rename(original);self.database.symlink_to(original)
        with self.assertRaises(FreeAIError):
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)

    async def test_fresh_state_requires_no_database_or_existing_encryption_key(self):
        self.database.unlink()
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'RECOVERY_STATE_MISMATCH')
        self.recovery.abandon();self.keys.get.return_value=None
        receipt=await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(receipt['kind'],'fresh')
        self.assertEqual(await self.recovery.verify(receipt['id'],artifacts=self.artifacts),receipt)
        self.keys.save_recovery.assert_not_called()

    async def test_corrupt_db_failed_snapshot_and_abandon_requires_new_connection_check(self):
        self.database.write_bytes(b'not SQLite')
        self.state.update(enabled=True,configured=True,free_plan='user-confirmed',verified_routes=['openai/gpt-oss-120b','openai/gpt-oss-20b'])
        with self.assertRaises(FreeAIError):
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.recovery.abandon()
        self.assertFalse(self.state.value['enabled'])
        self.assertEqual(self.state.value['verified_routes'],[])
        self.assertFalse(self.recovery.pending())
        self.assertEqual(self.database.read_bytes(),b'not SQLite')

    async def test_current_prepared_database_restore_and_lost_key_recovery_keep_gate_closed(self):
        receipt = await self.recovery.snapshot(self.database, artifacts=self.artifacts)
        self.database.write_bytes(b"corrupt after interrupted package change")
        self.keys.get.return_value = None
        async def restore_key(value):
            self.keys.get.return_value = value
        self.keys.create = AsyncMock(side_effect=restore_key)
        result = await self.recovery.restore_prepared(receipt['id'], artifacts=self.artifacts)
        self.assertTrue(result['restored'])
        self.keys.create.assert_awaited_once_with(KEY)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT value FROM settings WHERE key='quota'").fetchone(), ('7',))
        await self.recovery.verify_key(self.database, KEY)
        self.assertTrue(self.recovery.pending())
        self.assertFalse(self.state.value['enabled'])
        self.assertEqual(self.state.value['verified_routes'], [])

    async def test_restore_does_not_replace_a_changed_key_or_replay_historical_state(self):
        receipt = await self.recovery.snapshot(self.database, artifacts=self.artifacts)
        original = self.database.read_bytes()
        self.keys.get.return_value = 'b' * 64
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.restore_prepared(receipt['id'], artifacts=self.artifacts)
        self.assertEqual(error.exception.code, 'RECOVERY_KEY_CHANGED')
        self.assertEqual(self.database.read_bytes(), original)
        self.recovery.abandon()
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.restore_prepared(receipt['id'], artifacts=self.artifacts)
        self.assertEqual(error.exception.code, 'RECOVERY_NOT_PREPARED')

    async def test_reserved_snapshot_and_nonce_binding_survive_lost_root_reply(self):
        identity = 'e' * 32
        operation = {'schema':1,'transactionId':identity,'nonce_sha256':'f' * 64}
        receipt = await self.recovery.snapshot(self.database, artifacts=self.artifacts, reserved_id=identity, operation=operation)
        self.assertEqual(receipt['id'],identity)
        restarted = Recovery(self.state,self.keys,NODE)
        self.assertEqual(await restarted.verify(identity,artifacts=self.artifacts),receipt)
        restarted.verify_operation(identity,operation)
        with self.assertRaises(FreeAIError):
            restarted.verify_operation(identity,operation|{'nonce_sha256':'0' * 64})
        self.assertEqual(json.loads(restarted.marker.read_text())['id'],identity)
        self.assertNotIn(KEY,(restarted.root / identity / 'operation.json').read_text())

    async def test_invalid_reserved_binding_creates_no_marker_or_snapshot(self):
        with self.assertRaises(FreeAIError):
            await self.recovery.snapshot(self.database, artifacts=self.artifacts, reserved_id='../bad', operation={})
        self.assertFalse(self.recovery.pending())
        self.assertEqual(list(self.recovery.root.iterdir()),[])

    async def test_disk_operation_rejects_boolean_schema_and_duplicate_fields(self):
        identity = 'e' * 32
        operation = {'schema':1,'transactionId':identity,'nonce_sha256':'f' * 64}
        await self.recovery.snapshot(self.database, artifacts=self.artifacts, reserved_id=identity, operation=operation)
        path = self.recovery.root / identity / 'operation.json'
        malformed = [
            json.dumps(operation | {'schema':True}),
            '{"schema":1,"transactionId":"' + identity + '","nonce_sha256":"' + '0' * 64 + '","nonce_sha256":"' + 'f' * 64 + '"}',
        ]
        for value in malformed:
            with self.subTest(value=value):
                path.write_text(value)
                with self.assertRaises(FreeAIError) as error:
                    self.recovery.verify_operation(identity,operation)
                self.assertEqual(error.exception.code,'RECOVERY_BINDING_INVALID')

    async def test_snapshot_parent_is_durable_before_key_or_database_work(self):
        events = []
        def synced(path):
            events.append(Path(path))
            sync_directory(path)
        async def get_key():
            self.assertEqual(events[0],self.recovery.root)
            return KEY
        self.keys.get.side_effect = get_key
        with patch('maslow_free_ai.recovery.sync_directory',side_effect=synced):
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(events[0],self.recovery.root)

    async def test_snapshot_parent_sync_failure_blocks_database_and_key_work(self):
        with patch('maslow_free_ai.recovery.sync_directory',side_effect=OSError(28,'No space')):
            with self.assertRaises(FreeAIError) as error:
                await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'RECOVERY_SNAPSHOT_FAILED')
        self.keys.get.assert_not_awaited()
        self.assertTrue(self.recovery.pending())
        self.assertEqual(list(self.recovery.root.glob('*/receipt.json')),[])

    async def test_duplicate_prepare_does_not_replace_previous_snapshot(self):
        receipt=await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        with self.assertRaises(FreeAIError) as error:
            await self.recovery.snapshot(self.database,artifacts=self.artifacts)
        self.assertEqual(error.exception.code,'RECOVERY_PENDING')
        self.assertEqual([x.name for x in self.recovery.root.iterdir()],[receipt['id']])


class RecoverySecretTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovery_secret_is_stdin_only_and_identity_cannot_inject_args(self):
        keys=EncryptionKey();keys._get=AsyncMock(side_effect=[None,KEY]);keys._run=AsyncMock(return_value=(0,''))
        identity='d'*32
        await keys.save_recovery(identity,KEY)
        args,secret=keys._run.await_args.args
        self.assertEqual(secret,KEY)
        self.assertNotIn(KEY,' '.join(args))
        self.assertEqual(args[-1],'recovery-'+identity)
        with self.assertRaises(FreeAIError):
            await keys.get_recovery('../encryption')

    async def test_existing_other_recovery_secret_is_not_replaced(self):
        keys=EncryptionKey();keys._get=AsyncMock(return_value='b'*64);keys._run=AsyncMock()
        with self.assertRaises(FreeAIError):
            await keys.save_recovery('d'*32,KEY)
        keys._run.assert_not_called()
