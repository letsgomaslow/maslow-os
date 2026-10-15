"""Real Secret Service proof on a disposable D-Bus/home, synthetic keys only.

Does not inspect or modify the person's desktop keyring. No inference/account
request is submitted. Installed-product/keyring UX remains a separate gate.
"""

import asyncio
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import subprocess
import re
import signal
import sqlite3
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'free_ai'))
from maslow_free_ai.credentials import EncryptionKey
from maslow_free_ai.errors import FreeAIError
from maslow_free_ai.recovery import Recovery
from maslow_free_ai.state import State


async def bounded_output(process):
    try:
        return await asyncio.wait_for(process.communicate(),10)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise


async def recovery_probe(keys):
    """Real SQLite/WAL, Node crypto and disposable Secret Service; no packages."""
    node = Path('/tmp/maslow-freellmapi-tools/node-v22.23.3-linux-x64/bin/node')
    if not node.is_file():
        node = Path('/usr/lib/maslow-free-ai/node/bin/node')
    version = await asyncio.create_subprocess_exec(str(node),'--version',stdout=asyncio.subprocess.PIPE)
    output, _ = await bounded_output(version)
    assert version.returncode == 0 and output == b'v22.23.3\n'
    encrypt = """const c=require('node:crypto'),iv=c.randomBytes(16),e=c.createCipheriv('aes-256-gcm',Buffer.from('a'.repeat(64),'hex'),iv);const v=e.update('gsk_'+'f'.repeat(32),'utf8','hex')+e.final('hex');process.stdout.write(JSON.stringify([v,iv.toString('hex'),e.getAuthTag().toString('hex')]));"""
    child = await asyncio.create_subprocess_exec(str(node),'--eval',encrypt,stdout=asyncio.subprocess.PIPE)
    output, _ = await bounded_output(child)
    assert child.returncode == 0
    ciphertext,iv,tag = json.loads(output)
    state = State()
    state.update(configured=True,enabled=True,free_plan='user-confirmed',verified_routes=['openai/gpt-oss-120b','openai/gpt-oss-20b'])
    recovery = Recovery(state,keys,node)
    database = state.directory / 'router.sqlite3'
    identity = 'e' * 32
    operation = {'schema':1,'transactionId':identity,'nonce_sha256':hashlib.sha256(('f' * 64).encode('ascii')).hexdigest()}
    artifacts = {'maslow-free-ai':'1' * 64,'maslow-voice':'2' * 64}
    with closing(sqlite3.connect(database)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE api_keys(platform TEXT, encrypted_key TEXT, iv TEXT, auth_tag TEXT)')
        db.execute('INSERT INTO api_keys VALUES(?,?,?,?)',('groq',ciphertext,iv,tag))
        db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
        db.execute("INSERT INTO settings VALUES('quota','8')")
        db.commit()
        for path in (database,Path(str(database)+'-wal'),Path(str(database)+'-shm')):
            path.chmod(0o600)
        receipt = await recovery.snapshot(database,artifacts=artifacts,reserved_id=identity,operation=operation)
    restarted = Recovery(State(),keys,node)
    restarted.verify_operation(identity,operation)
    assert await restarted.verify(identity,artifacts=artifacts) == receipt
    assert await keys.get_recovery(identity) == 'a' * 64
    try:
        restarted.verify_operation(identity,operation | {'nonce_sha256':'0' * 64})
    except FreeAIError as error:
        assert error.code == 'RECOVERY_BINDING_INVALID'
    else:
        raise RuntimeError('Wrong root operation was accepted')
    database.write_bytes(b'disposable interrupted database')
    clear = await asyncio.create_subprocess_exec('/usr/bin/secret-tool','clear','application','maslow-free-ai','account','encryption',
        stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
    await bounded_output(clear)
    assert clear.returncode == 0 and await keys.get() is None
    restored = await restarted.restore_prepared(identity,artifacts=artifacts)
    assert restored['restored'] and await keys.get() == 'a' * 64
    await restarted.verify_key(database,await keys.get())
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("SELECT value FROM settings WHERE key='quota'").fetchone() == ('8',)
        assert db.execute('SELECT encrypted_key,iv,auth_tag FROM api_keys').fetchone() == (ciphertext,iv,tag)
        assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    assert restarted.pending() and not restarted.state.value['enabled'] and restarted.state.value['verified_routes'] == []
    for path in (restarted.root / identity).iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
        assert ('a' * 64).encode() not in path.read_bytes()
        assert ('gsk_'+'f' * 32).encode() not in path.read_bytes()
    restarted.abandon()
    try:
        await restarted.restore_prepared(identity,artifacts=artifacts)
    except FreeAIError as error:
        assert error.code == 'RECOVERY_NOT_PREPARED'
    else:
        raise RuntimeError('Historical database restore was accepted')
    return {'wal_committed_quota_retained':True,'root_operation_binding_rechecked_after_restart':True,
        'wrong_nonce_rejected':True,'corrupt_database_and_missing_active_key_restored':True,
        'matching_ciphertext_and_secret_retained':True,'admission_remained_closed':True,
        'snapshot_permissions_and_plaintext_exclusion_checked':True,'historical_restore_rejected':True,
        'package_restore_verified':False}


async def probe(recovery=False):
    home = Path(os.environ['HOME'])
    if (os.environ.get('MASLOW_PRIVATE_KEYRING_PROBE') != '1' or home.parent != Path(tempfile.gettempdir())
            or not home.name.startswith('maslow-keyring-probe-') or home.is_symlink()
            or home.stat().st_uid != os.getuid() or stat.S_IMODE(home.stat().st_mode) != 0o700):
        raise RuntimeError('Private child requires the disposable outer probe')
    for variable,name in (('XDG_RUNTIME_DIR','runtime'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state')):
        if os.environ.get(variable) != str(home / name):
            raise RuntimeError('Private child requires disposable XDG paths')
    bus_owner = await asyncio.create_subprocess_exec('/usr/bin/gdbus','call','--session','--dest',
        'org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method',
        'org.freedesktop.DBus.GetConnectionUnixProcessID','org.freedesktop.DBus',
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    output, _ = await bounded_output(bus_owner)
    match = re.fullmatch(rb"\(uint32 ([0-9]+),\)\n",output)
    assert bus_owner.returncode == 0 and match
    bus_pid = int(match[1])
    bus_env = dict(item.split(b'=',1) for item in Path('/proc/'+str(bus_pid)+'/environ').read_bytes().split(b'\x00') if b'=' in item)
    if (Path('/proc/'+str(bus_pid)).stat().st_uid != os.getuid() or bus_env.get(b'HOME') != str(home).encode()
            or bus_env.get(b'XDG_RUNTIME_DIR') != str(home / 'runtime').encode()):
        raise RuntimeError('DBus is not the disposable session')
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    loop.add_signal_handler(signal.SIGTERM,task.cancel)
    directory = Path(os.environ['XDG_RUNTIME_DIR']) / 'keyring'
    directory.mkdir(mode=0o700)
    daemon = await asyncio.create_subprocess_exec('/usr/bin/gnome-keyring-daemon', '--foreground', '--unlock',
        '--components=secrets', '--control-directory=' + str(directory), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    service_handle = None
    try:
        daemon.stdin.write(b'disposable-probe-password')
        await daemon.stdin.drain()
        daemon.stdin.close()
        # Poll DBus itself without activating Secret Service or reading keys.
        for _ in range(30):
            registered = await asyncio.create_subprocess_exec('/usr/bin/gdbus','call','--session','--dest',
                'org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method',
                'org.freedesktop.DBus.NameHasOwner','org.freedesktop.secrets',
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
            output, _ = await bounded_output(registered)
            if registered.returncode == 0 and output == b'(true,)\n':
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError('Disposable Secret Service did not become ready')
        owner = await asyncio.create_subprocess_exec('/usr/bin/gdbus', 'call', '--session', '--dest',
            'org.freedesktop.DBus', '--object-path', '/org/freedesktop/DBus', '--method',
            'org.freedesktop.DBus.GetConnectionUnixProcessID', 'org.freedesktop.secrets',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        output, _ = await bounded_output(owner)
        match = re.fullmatch(rb"\(uint32 ([0-9]+),\)\n", output)
        assert owner.returncode == 0 and match
        service_pid = int(match[1])
        candidate_handle = os.pidfd_open(service_pid)
        process_env = dict(item.split(b'=', 1) for item in Path('/proc/' + str(service_pid) + '/environ').read_bytes().split(b'\x00') if b'=' in item)
        if (process_env.get(b'HOME') != os.environ['HOME'].encode()
                or process_env.get(b'DBUS_SESSION_BUS_ADDRESS') != os.environ['DBUS_SESSION_BUS_ADDRESS'].encode()
                or Path('/proc/' + str(service_pid)).stat().st_uid != os.getuid()):
            os.close(candidate_handle)
            raise RuntimeError('Secret Service did not belong to the disposable session')
        service_handle = candidate_handle
        keys = EncryptionKey()
        assert await keys.get() is None
        await keys.create('a' * 64)
        assert await keys.get() == 'a' * 64
        await keys.save_recovery('d' * 32, 'a' * 64)
        assert await keys.get_recovery('d' * 32) == 'a' * 64
        recovery_result = await recovery_probe(keys) if recovery else None
        lock = await asyncio.create_subprocess_exec('/usr/bin/gdbus', 'call', '--session', '--dest', 'org.freedesktop.secrets',
            '--object-path', '/org/freedesktop/secrets', '--method', 'org.freedesktop.Secret.Service.Lock',
            "['/org/freedesktop/secrets/collection/login']", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await bounded_output(lock)
        assert lock.returncode == 0
        for operation in (keys.get, lambda: keys.get_recovery('d' * 32)):
            try:
                await operation()
            except FreeAIError as error:
                assert error.code == 'KEYRING_LOCKED'
            else:
                raise RuntimeError('Locked collection was treated as missing')
        print(json.dumps({'schema':1,'backend':'real GNOME Keyring / private D-Bus',
            'missing_key':True,'private_stdin_store_roundtrip':True,'recovery_secret_roundtrip':True,
            'locked_active_and_recovery_keys_rejected':True,'host_keyring_touched':False,
            'live_provider_requests':0,'installed_product_verified':False,
            **({'recovery':recovery_result} if recovery else {})}))
    finally:
        if service_handle is not None:
            try:
                signal.pidfd_send_signal(service_handle, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.close(service_handle)
        if daemon.returncode is None:
            daemon.terminate()
        try:
            await asyncio.wait_for(daemon.wait(), 5)
        except TimeoutError:
            daemon.kill()
            await daemon.wait()
        loop.remove_signal_handler(signal.SIGTERM)


def main():
    if sys.argv[1:] in (['--private-child'],['--private-recovery-child']):
        asyncio.run(probe(recovery=sys.argv[1:] == ['--private-recovery-child']))
        return
    if sys.argv[1:] not in ([],['--recovery']):
        raise SystemExit('Only --recovery is accepted.')
    with tempfile.TemporaryDirectory(prefix='maslow-keyring-probe-') as temporary:
        directory = Path(temporary)
        env = {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(directory),'PYTHONDONTWRITEBYTECODE':'1','MASLOW_PRIVATE_KEYRING_PROBE':'1'}
        for variable,name in (('XDG_RUNTIME_DIR','runtime'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state')):
            path=directory / name;path.mkdir(mode=0o700);env[variable]=str(path)
        child_mode = '--private-recovery-child' if sys.argv[1:] else '--private-child'
        process = subprocess.Popen(['/usr/bin/dbus-run-session','--',sys.executable,str(Path(__file__).resolve()),child_mode],
            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=60)
        finally:
            # Terminate only this newly created group, including failure paths.
            # The child's SIGTERM handler also releases the validated keyring
            # owner's pidfd even if GNOME moved that owner to another group.
            try:
                os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=5)
        if process.returncode:
            raise SystemExit('Disposable keyring proof failed: '+ stderr[-2000:])
        lines = [line for line in stdout.splitlines() if line.startswith('{')]
        if len(lines) != 1:
            raise SystemExit('Disposable keyring proof returned an invalid receipt')
        print(json.dumps(json.loads(lines[0])))


if __name__ == '__main__':
    main()
