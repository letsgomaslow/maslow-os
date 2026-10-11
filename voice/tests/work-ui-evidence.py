"""Exercise an already running isolated ui-preview fixture using native input.

Requires a disposable container with Sway, Quickshell, grim, wtype and a
Wayland virtual-pointer click helper; never target the user's desktop.
The coordinator owns compositor startup and teardown.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--container', required=True)
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--sway-socket', required=True)
args = parser.parse_args()
base = ['docker', 'exec', '-e', 'XDG_RUNTIME_DIR=/evidence/isolated', '-e', 'WAYLAND_DISPLAY=wayland-1', '-e', f'SWAYSOCK={args.sway_socket}', args.container]

def execute(*command):
    return subprocess.check_output(base + list(command), text=True).strip()

def ipc(method, *values):
    return execute('qs', '-p', '/evidence/ui-config', 'ipc', 'call', 'voice-fixture', method, *[str(v).lower() if isinstance(v, bool) else str(v) for v in values])

def state():
    return json.loads(ipc('composerStatus'))

def requests():
    return json.loads(ipc('requests'))

def click(x, y):
    execute('/tmp/qa-click', str(x), str(y), '1280', '960')
    time.sleep(.15)

def capture(name):
    time.sleep(.2)
    execute('grim', f'/evidence/{name}.png')

ipc('page', 'tasks')
ipc('composer', '', '', '', '', False)
click(780, 438)
execute('wtype', '-s', '200', '-d', '20', '/fixture/work')
click(780, 500)
execute('wtype', '-s', '200', '-d', '20', 'Draft a concise project summary')
assert state()['project'] == '/fixture/work'
assert state()['draft'] == 'Draft a concise project summary'
capture('work-existing-filled')
click(775, 596)
click(775, 596)
submitted = [r for r in requests() if r['action'] == 'task_submit']
assert len(submitted) == 1, submitted
assert submitted[0]['execution_connection'] == 'existing'
assert submitted[0]['capabilities'] == {}
original_id = submitted[0]['request_id']
ipc('composerTransportError')
assert not state()['submitting'] and state()['draft'] == 'Draft a concise project summary'
assert 'Retry' in state()['feedback']
capture('work-transport-retry')
click(775, 625)
retried = [r for r in requests() if r['action'] == 'task_submit']
assert len(retried) == 2 and retried[-1]['request_id'] == original_id
ipc('composerResponse', True, '')
assert state()['draft'] == '' and not state()['submitting']
ipc('assistantReadiness', True, True)
# Select the real connection control; then model the daemon's confirmed update.
click(950, 410)
click(950, 511)
assert any(r['action'] == 'configure' and r.get('settings', {}).get('execution_connection') == 'free-cloud' for r in requests())
ipc('preference', 'execution_connection', 'free-cloud')
ipc('composer', 'Summarize the selected documents', '/fixture/work', ' first.md\n\nsecond.txt \n', 'summary.md', False)
capture('work-free-cloud')
args.evidence.mkdir(parents=True, exist_ok=True)
# A typed note path alone is not permission to save it.
click(775, 824)
free = [r for r in requests() if r['action'] == 'task_submit'][-1]
assert free['execution_connection'] == 'free-cloud'
assert free['capabilities']['documents'] == ['first.md', 'second.txt']
assert free['capabilities']['note'] is None
assert not any(r['action'] in ('start_voice', 'toggle_voice') for r in requests())
ipc('composerResponse', False, 'Fixture request was rejected. Draft preserved.')
assert state()['draft'] == 'Summarize the selected documents' and not state()['submitting']
click(697, 728)
assert state()['saveNote'] is True
execute('wtype', '-s', '200', '-k', 'Next')
capture('work-note-consent')
click(775, 787)
with_note = [r for r in requests() if r['action'] == 'task_submit'][-1]
assert with_note['capabilities']['note'] == 'summary.md'
assert with_note['request_id'] != free['request_id']
ipc('composerResponse', False, 'Fixture request was rejected. Draft preserved.')
ipc('assistantReadiness', True, False)
before_unready = len(requests())
click(775, 787)
assert len(requests()) == before_unready, 'unready connection must disable submission'
capture('work-unready')
ipc('assistantReadiness', True, True)
# Resize the actual output, retaining the open Work surface and grants.
execute('swaymsg', 'output HEADLESS-1 mode 480x800')
execute('wtype', '-s', '200', '-k', 'Prior')
capture('work-narrow-top')
execute('wtype', '-s', '200', '-k', 'Next')
capture('work-narrow-note')
geometry = json.loads(ipc('geometry'))
assert geometry['width'] == 480 and geometry['card']['width'] <= 448
assert geometry['card']['x'] >= 0 and geometry['card']['y'] >= 0
assert geometry['card']['x'] + geometry['card']['width'] <= geometry['width']
assert geometry['card']['y'] + geometry['card']['height'] <= geometry['height']
(args.evidence / 'work-interaction.json').write_text(json.dumps({'status': state(), 'geometry': geometry, 'requests': requests()}, indent=2) + '\n')
print('Native Work input, request identity, transport recovery, grants, readiness and resize checks passed.')
