#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
if ! command -v quickshell >/dev/null 2>&1; then
  skip "quickshell not installed; skipping real Qt background service lifecycle"
  exit 0
fi
require_command python3

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/services" "$stage/runtime"
chmod 700 "$stage/runtime"
cp "$ROOT/shell/services/AuthServiceStore.js" "$stage/services/"
# Exercise the actual production methods in a small real-Qt host. No loader,
# Component, status signal or QObject lifetime is mocked.
python3 - "$stage" <<'PY'
import os
import pathlib
import re
import sys
root = pathlib.Path(os.environ['ROOT'])
stage = pathlib.Path(sys.argv[1])
source = (root / 'shell/shell.qml').read_text()
methods = []
for name in ('isAuthenticationService', 'backgroundServiceLoadCurrent',
             'cancelBackgroundServiceLoad', 'ensureService', '_syncServices',
             'serviceKeepLoaded', 'unloadPluginServices'):
  match = re.search(r'^  function ' + name + r'\([^\n]*\) \{[\s\S]*?^  \}', source, re.M)
  assert match, 'missing actual production method ' + name
  methods.append(match.group())
fixture = (root / 'test/shell.d/fixtures/background-service-loading/shell.qml').read_text()
(stage / 'shell.qml').write_text(fixture.replace('  // PRODUCTION_METHODS', '\n\n'.join(methods)))
service = '''import QtQuick
Item {
  id: service
  property int ticks: 0
  readonly property string mirroredPath: shell ? shell.omarchyPath : ""
  signal heartbeat(int count)
  function touch() { return tag + ":" + mirroredPath }
  Timer {
    interval: 10
    repeat: true
    running: true
    onTriggered: { service.ticks++; service.heartbeat(service.ticks) }
  }
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null
  property var barWidgetRegistry: null
  property string omarchyPath: ""
  property string tag: "TAG"
  onShellChanged: if (shell && shell.cancelDuringInjection) shell.disableBackground()
  Component.onCompleted: if (parent) parent.host.created++
  Component.onDestruction: if (parent) parent.host.destroyed++
}
'''
for tag in ('a', 'b'):
  for prefix in ('', *(str(i) + '-' for i in range(1, 21))):
    (stage / (prefix + tag + '.qml')).write_text(service.replace('TAG', tag))
for prefix in ('', *(str(i) + '-' for i in range(1, 21))):
  (stage / (prefix + 'broken.qml')).write_text('import QtQuick\nQtObject { intentionally invalid syntax }\n')
PY
output=$(XDG_RUNTIME_DIR="$stage/runtime" QT_QPA_PLATFORM=offscreen timeout 20 quickshell -p "$stage" --no-color 2>&1) || fail "real Qt background service lifecycle exits cleanly" "$output"
[[ $output == *"RESULT pass"* ]] || fail "real Qt background service lifecycle assertions pass" "$output"
if rg -q 'RESULT fail|ReferenceError|TypeError|Unable to assign|Binding loop|Cannot call method|Invalid attempt to destroy' <<<"$output"; then
  fail "background service lifecycle has no unexpected QML errors" "$output"
fi
pass "real async background loading suppresses duplicates and publishes fresh metadata"
pass "disable/remove/source replacement/reload cancel stale real Qt component loads"
pass "load errors release claims and creation-time cancellation prevents publication"
pass "third-party/auth service parenting and keepLoaded identity remain unchanged"
