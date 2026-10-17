#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

fixture_dir=$(mktemp -d)
trap 'rm -rf "$fixture_dir"' EXIT
export MASLOW_LOCK_FIXTURE="$fixture_dir/shell.qml"

run_node_test <<'JS'
const fs = require('fs')
const source = fs.readFileSync(path.join(root, 'shell/shell.qml'), 'utf8')
const voice = fs.readFileSync(path.join(root, 'voice/ui/Panel.qml'), 'utf8')
function hostFunction(name) {
  const match = source.match(new RegExp('^  function ' + name + '\\([^]*?^  }', 'm'))
  assert(match, `host function exists: ${name}`)
  return match[0]
}
const functions = ['maslowVoiceLockAllowed', 'packagedVoiceLockStatus', 'observeMaslowVoiceLock', 'forgetMaslowVoiceLock'].map(hostFunction).join('\n')
const component = source.match(/^  Component \{\n    id: maslowVoiceLockStatusComponent[^]*?^  }/m)
assert(component, 'host declares the scalar status component')
const statusProperty = source.match(/^  readonly property QtObject _maslowVoiceLockStatus:.*$/m)
assert(statusProperty, 'host constructs a stable status proxy outside caller bindings')
const lookup = source.match(/_serviceLookup: function\(requestedId\) \{([^]*?)^      },/m)
assert(lookup, 'extract the actual scoped service lookup')
assert(/key === "omarchy.lock" && manifest.__isFirstParty\)\s*shell.observeMaslowVoiceLock\(inst\)/.test(source), 'only the actual trusted first-party lock producer publishes status')
assert(!/property\s+(?:var|QtObject)\s+_maslowVoice.*(?:inst|Service)/.test(source), 'no authentication object is stored on the public shell')
const voiceBindings = [
  /^  readonly property var lockService:.*$/m,
  /^  readonly property bool sessionLocked:.*$/m,
  /^  onSessionLockedChanged:.*$/m
].map(pattern => { const match = voice.match(pattern); assert(match, 'existing Voice lock handler remains present'); return match[0] }).join('\n').replace(/\bshell\b/g, 'voiceSelf.shell')
fs.writeFileSync(process.env.MASLOW_LOCK_FIXTURE, `
import QtQuick
import Quickshell
ShellRoot {
  id: shell
  property bool _maslowVoiceSessionLocked: true
  property int _maslowVoiceLockGeneration: 0
  ${statusProperty[0]}
  property var errors: []
  property int phase: 0
  property int baselineClose: 0
  property var commands: []
  property int ordinaryLookups: 0
  property QtObject pluginRegistry: QtObject {
    property bool enabled: true
    property var installedPlugins: ({ "maslow.voice": { __isPackaged: true, __sourceDir: "/usr/share/maslow/plugins/maslow.voice" } })
    function isEnabled(id) { return enabled && id === "maslow.voice" }
  }
  property QtObject firstLock: QtObject { property bool locked: false; property string password: "synthetic-private"; function unlock() {} }
  property QtObject nextLock: QtObject { property bool locked: false }
  property QtObject facade: QtObject {
    function recordCommand(command) { shell.commands = shell.commands.concat([command]) }
    function serviceFor(requestedId) {
      var key = "maslow.voice"
      var allowOwnService = true
      ${lookup[1]}
    }
  }
  property QtObject voicePanel: QtObject {
    id: voiceSelf
    property var shell: facade
    property int closeCount: 0
    function close() { closeCount++ }
    function send(command) { voiceSelf.shell.recordCommand(command) }
    ${voiceBindings}
  }
  function pluginServiceFor(owner, requested) { ordinaryLookups++; return null }
  function check(value, description) { if (!value) errors = errors.concat([description]) }
  ${component[0]}
  ${functions}
  Component.onCompleted: {
    check(voicePanel.sessionLocked, "unknown producer starts actual Voice binding locked")
    observeMaslowVoiceLock(firstLock)
    packagedVoiceLockStatus("maslow.voice", "omarchy.lock")
  }
  Timer {
    interval: 60; running: true; repeat: true
    onTriggered: {
      var proxy = shell._maslowVoiceLockStatus
      if (!proxy) {
        console.log("MASLOW_VOICE_LOCK_RESULT " + JSON.stringify({ok: false, errors: ["proxy unavailable"]}))
        Qt.quit()
        return
      }
      if (shell.phase === 0) {
        shell.check(proxy && !proxy.locked && !shell.voicePanel.sessionLocked, "unlocked status reaches unchanged Voice binding")
        shell.check(shell.ordinaryLookups === 0, "lock status never queries an ordinary or provider service")
        shell.check(proxy.parent == null && proxy.password === undefined && proxy.unlock === undefined, "proxy has no auth data/methods/parent")
        var refused = false
        try { proxy.locked = true } catch (error) { refused = true }
        shell.check(refused && !proxy.locked, "status property is read-only")
        shell.baselineClose = shell.voicePanel.closeCount
        shell.firstLock.locked = true
      } else if (shell.phase === 1) {
        shell.check(shell.voicePanel.sessionLocked && shell.voicePanel.closeCount > shell.baselineClose, "lock push closes existing Voice UI")
        shell.check(shell.commands.length > 0 && shell.commands.every(function(command) { return command === "end_voice" }), "lock push only ends Voice, never starts providers")
        shell.pluginRegistry.enabled = false
      } else if (shell.phase === 2) {
        shell.check(proxy.locked && shell.voicePanel.sessionLocked && shell.packagedVoiceLockStatus("maslow.voice", "omarchy.lock") === proxy, "disable revokes fresh and retained access fail-closed")
        shell.pluginRegistry.enabled = true
        shell.forgetMaslowVoiceLock("omarchy.lock")
        shell.check(proxy.locked, "service teardown fails closed")
        shell.observeMaslowVoiceLock(shell.nextLock)
        shell.firstLock.locked = false
        shell.firstLock.locked = true
      } else if (shell.phase === 3) {
        shell.check(!proxy.locked, "stale former lock signal cannot overwrite replacement state")
        shell.check(shell.packagedVoiceLockStatus("omadock", "omarchy.lock") === null, "other plugins cannot obtain proxy")
        shell.check(shell.packagedVoiceLockStatus("maslow.voice", "omarchy.polkit") === null, "other authentication ids remain unavailable")
        shell.pluginRegistry.installedPlugins = ({ "maslow.voice": { __isPackaged: false, __sourceDir: "/usr/share/maslow/plugins/maslow.voice" } })
      } else if (shell.phase === 4) {
        shell.check(proxy.locked && shell.voicePanel.sessionLocked && shell.packagedVoiceLockStatus("maslow.voice", "omarchy.lock") === proxy, "unpackaged manifest cannot retain or request live state")
        shell.pluginRegistry.installedPlugins = ({ "maslow.voice": { __isPackaged: true, __sourceDir: "/home/untrusted/maslow.voice" } })
      } else if (shell.phase === 5) {
        shell.check(proxy.locked && shell.voicePanel.sessionLocked && shell.packagedVoiceLockStatus("maslow.voice", "omarchy.lock") === proxy, "untrusted package source path is rejected")
        shell.pluginRegistry = null
      } else if (shell.phase === 6) {
        shell.check(proxy.locked && shell.voicePanel.sessionLocked, "missing registry keeps actual Voice binding locked")
        console.log("MASLOW_VOICE_LOCK_RESULT " + JSON.stringify({ok: shell.errors.length === 0, errors: shell.errors, commands: shell.commands}))
        Qt.quit()
      }
      shell.phase++
    }
  }
}
`)
JS

if ! command -v quickshell >/dev/null; then
  skip "quickshell not installed; skipping scalar lock facade runtime fixture"
  exit 0
fi
require_command jq

# Isolate the extracted production component/functions and the unchanged Voice
# binding. This does not load the complete shell or bypass OmarchyLoadPatch.
mkdir -m700 "$fixture_dir/runtime" "$fixture_dir/home"
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
XDG_RUNTIME_DIR="$fixture_dir/runtime" HOME="$fixture_dir/home" \
  timeout 10s quickshell -p "$MASLOW_LOCK_FIXTURE" --no-color >"$fixture_dir/log" 2>&1 || {
    cat "$fixture_dir/log" >&2
    fail "scalar lock facade runtime fixture loaded and exited"
  }
result=$(sed -n 's/.*MASLOW_VOICE_LOCK_RESULT //p' "$fixture_dir/log" | tail -1)
if [[ -z $result ]] || ! jq -e '.ok == true' <<<"$result" >/dev/null; then
  cat "$fixture_dir/log" >&2
  fail "packaged Voice receives only immutable pushed scalar lock state"
fi
pass "packaged Voice receives only immutable pushed scalar lock state"
