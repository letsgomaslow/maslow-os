"""Real Secret Service proof on a disposable D-Bus/home, synthetic keys only.

Does not inspect or modify the person's desktop keyring. No inference/account
request is submitted. Installed-product/keyring UX remains a separate gate.
"""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import re
import signal
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'free_ai'))
from maslow_free_ai.credentials import EncryptionKey
from maslow_free_ai.errors import FreeAIError


async def probe():
    directory = Path(os.environ['XDG_RUNTIME_DIR']) / 'keyring'
    directory.mkdir(mode=0o700)
    daemon = await asyncio.create_subprocess_exec('/usr/bin/gnome-keyring-daemon', '--foreground', '--unlock',
        '--components=secrets', '--control-directory=' + str(directory), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    daemon.stdin.write(b'disposable-probe-password')
    await daemon.stdin.drain()
    daemon.stdin.close()
    service_handle = None
    try:
        keys = EncryptionKey()
        for _ in range(30):
            try:
                assert await keys.get() is None
                break
            except FreeAIError:
                await asyncio.sleep(0.1)
        else:
            raise RuntimeError('Disposable Secret Service did not become ready')
        owner = await asyncio.create_subprocess_exec('/usr/bin/gdbus', 'call', '--session', '--dest',
            'org.freedesktop.DBus', '--object-path', '/org/freedesktop/DBus', '--method',
            'org.freedesktop.DBus.GetConnectionUnixProcessID', 'org.freedesktop.secrets',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        output, _ = await owner.communicate()
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
        await keys.create('a' * 64)
        assert await keys.get() == 'a' * 64
        await keys.save_recovery('d' * 32, 'a' * 64)
        assert await keys.get_recovery('d' * 32) == 'a' * 64
        lock = await asyncio.create_subprocess_exec('/usr/bin/gdbus', 'call', '--session', '--dest', 'org.freedesktop.secrets',
            '--object-path', '/org/freedesktop/secrets', '--method', 'org.freedesktop.Secret.Service.Lock',
            "['/org/freedesktop/secrets/collection/login']", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(lock.wait(), 5)
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
            'live_provider_requests':0,'installed_product_verified':False}))
    finally:
        if service_handle is not None:
            try:
                signal.pidfd_send_signal(service_handle, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.close(service_handle)
        if daemon.returncode is None:
            daemon.terminate()
        await asyncio.wait_for(daemon.wait(), 5)


def main():
    if sys.argv[1:] == ['--private-child']:
        asyncio.run(probe())
        return
    if sys.argv[1:]:
        raise SystemExit('No arguments are accepted.')
    with tempfile.TemporaryDirectory(prefix='maslow-keyring-probe-') as temporary:
        directory = Path(temporary)
        env = {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(directory),'PYTHONDONTWRITEBYTECODE':'1'}
        for variable,name in (('XDG_RUNTIME_DIR','runtime'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state')):
            path=directory / name;path.mkdir(mode=0o700);env[variable]=str(path)
        result = subprocess.run(['/usr/bin/dbus-run-session','--',sys.executable,str(Path(__file__).resolve()),'--private-child'],
            env=env,capture_output=True,text=True,timeout=60)
        if result.returncode:
            raise SystemExit('Disposable keyring proof failed: '+ result.stderr[-2000:])
        lines = [line for line in result.stdout.splitlines() if line.startswith('{')]
        if len(lines) != 1:
            raise SystemExit('Disposable keyring proof returned an invalid receipt')
        print(json.dumps(json.loads(lines[0])))


if __name__ == '__main__':
    main()
