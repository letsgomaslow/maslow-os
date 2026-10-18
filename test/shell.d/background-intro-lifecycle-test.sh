#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
# Exercise the actual fixture guards without a compositor. A missing phase or
# reordered callback must not be able to produce the fixture success marker.
run_node_test <<'JS'
const fs = require('fs')
const vm = require('vm')
const source = fs.readFileSync(path.join(root, 'test/shell.d/fixtures/background-intro-lifecycle/shell.qml'), 'utf8')
const names = ['advancePhase', 'allPhasesCompleted']
const methods = names.map(name => {
  const found = source.match(new RegExp('^  function ' + name + '\\([^\\n]*\\) \\{[\\s\\S]*?^  \\}', 'm'))
  if (!found) throw new Error('missing fixture method ' + name)
  return found[0]
}).join('\n')
function fixture() {
  const ctx = { phase: 'startup', phaseHistory: 'startup', failed: false, milestones: [] }
  ctx.console = { log: value => ctx.milestones.push(value) }
  ctx.test = ctx
  ctx.check = ok => { if (!ok) ctx.failed = true }
  vm.createContext(ctx)
  vm.runInContext(methods, ctx)
  return ctx
}
let ctx = fixture()
ctx.advancePhase('startup', 'cover')
assert(!ctx.allPhasesCompleted(), 'an omitted intro phase cannot pass')
ctx.advancePhase('cover', 'completion')
assert(ctx.failed && ctx.phase === 'cover' && !ctx.allPhasesCompleted(), 'out-of-order intro phases fail without advancing')
assertDeepEqual(ctx.milestones, ['MILESTONE intro-phase=cover'], 'invalid intro transitions cannot emit progress')
ctx = fixture()
for (const [from, to] of [['startup', 'cover'], ['cover', 'handoff'], ['handoff', 'completion'], ['completion', 'complete']]) ctx.advancePhase(from, to)
assert(ctx.allPhasesCompleted(), 'all ordered intro phases admit completion')
assertDeepEqual(ctx.milestones, ['cover', 'handoff', 'completion', 'complete'].map(phase => 'MILESTONE intro-phase=' + phase), 'progress records every admitted intro phase in order')
ctx.failed = true
assert(!ctx.allPhasesCompleted(), 'a prior negative invariant failure cannot pass after completion')
JS
# Run the exact staged fake launcher in both admission and failure cases.
# Its own watchdog prevents a missing marker from leaving an unbounded child.
require_command python3
python3 - <<'PY_CONTROL'
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

source = (Path(os.environ['ROOT']) / 'test/shell.d/background-intro-lifecycle-test.sh').read_text()
match = re.search(r"""cat >"\$stage/bin/omarchy-theme-bg-boot-intro" <<'SH'\n(.*?)\nSH""", source, re.S)
assert match, 'missing actual fake launcher'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    script = root / 'launcher'
    script.write_text(match.group(1) + '\n')
    frame = root / 'ready'
    log = root / 'starts'
    env = dict(os.environ, INTRO_TEST_FRAME_READY=str(frame), INTRO_TEST_LOG=str(log))
    def run_marker_case():
        child = subprocess.Popen(['bash', str(script)], env=env, start_new_session=True)
        try:
            time.sleep(0.15)
            assert child.poll() is None, 'launcher exited before the first-frame marker'
            frame.touch()
            assert child.wait(timeout=2) == 0
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
    run_marker_case()
    assert log.read_text().splitlines() == ['intro']
    frame.unlink()
    started = time.monotonic()
    child = subprocess.Popen(['bash', str(script)], env=env, start_new_session=True)
    try:
        assert child.wait(timeout=12) == 124, 'missing marker bypassed the launcher watchdog'
        assert time.monotonic() - started < 12
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)
    assert log.read_text().splitlines() == ['intro', 'intro']
print('ok - fake startup waits for its first frame and bounds a missing marker')
PY_CONTROL
require_compositor "background intro lifecycle test"
require_command quickshell

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/services" "$stage/bin" "$stage/home"
printf 'P6\n1 1\n255\n\377\377\377' >"$stage/cover.ppm"
cp "$ROOT/shell/services/BackgroundIntro.qml" "$stage/services/"
ln -s "$ROOT/shell/Commons" "$stage/Commons"
cp "$SHELL_TEST_DIR/fixtures/background-intro-lifecycle/shell.qml" "$stage/shell.qml"
cat >"$stage/bin/omarchy-theme-bg-boot-intro" <<'SH'
#!/bin/bash
printf 'intro\n' >>"$INTRO_TEST_LOG"
# The fixture, not scheduler speed, controls when startup video may finish.
# A missing marker still terminates; this never extends the outer QML budget.
deadline=$((SECONDS + 10))
while [[ ! -f $INTRO_TEST_FRAME_READY ]]; do
  if (( SECONDS >= deadline )); then exit 124; fi
  sleep 0.01
done
SH
chmod +x "$stage/bin/omarchy-theme-bg-boot-intro"
cat >"$stage/bin/owe" <<'SH'
#!/bin/bash
if [[ -f $INTRO_TEST_FRAME_READY ]]; then
  sleep 0.25
  printf '{"kind":"video","ready":true,"has_transition":false,"time_pos":0.05}\n'
else
  printf '{"kind":"video","ready":true,"has_transition":true,"time_pos":0}\n'
fi
SH
chmod +x "$stage/bin/owe"
if output=$(HOME="$stage/home" PATH="$stage/bin:$PATH" INTRO_TEST_LOG="$stage/starts" INTRO_TEST_COVER="$stage/cover.ppm" INTRO_TEST_FRAME_READY="$stage/video-ready" timeout 10 quickshell -p "$stage" --no-color 2>&1); then
  fixture_exit=0
else
  fixture_exit=$?
fi
qml_fixture_progress "$fixture_exit" "$output"
(( fixture_exit == 0 )) || fail "background intro fixture exits cleanly" "$output"
[[ $output == *"RESULT pass"* ]] || fail "background intro lifecycle assertions pass" "$output"
if rg -q 'RESULT fail|ReferenceError|TypeError|Error:|Unable to assign|Binding loop' <<<"$output"; then
  fail "background intro fixture has no QML errors" "$output"
fi
[[ $(wc -l <"$stage/starts") == 1 ]] || fail "recreating the background service does not run another launcher"
pass "the cover stays while waiting and remains off when OWE recreates the background service"
