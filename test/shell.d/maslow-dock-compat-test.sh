#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const vm = require('vm')
const nodeAssert = require('assert')
const source = fs.readFileSync(path.join(root, 'shell/services/PluginRegistry.qml'), 'utf8')
function extract(source, name) {
  const match = source.match(new RegExp('^  function ' + name + '\\([^]*?^  }', 'm'))
  assert(match, `production function exists: ${name}`)
  return match[0]
}
// Exercise production registry decisions and the actual user-config mutator.
// Placement/clone helpers must not be used for this ordinary service plugin.
const context = {
  config: null, installedPlugins: {'omarchy.dock': {__isFirstParty: true, kinds: ['service']}},
  lastEnableError: '', registryRevision: 0, console,
  Util: {isPlainObject: v => !!v && typeof v === 'object' && !Array.isArray(v), canonicalWidgetId: v => String(v || ''), barSections: ['left', 'center', 'right']},
  pluginsChanged() {}, activeCloneFor() { return '' },
  findBarLocation() { return {found: false} }
}
context.shellConfigProvider = () => context.config
context.shellConfigMutator = change => { context.config = JSON.parse(JSON.stringify(context.config)); change(context.config) }
vm.createContext(context)
for (const name of ['isEnabled', 'legacyMaslowLauncherConfigured', 'isDisabled', 'findEntryLocation', 'ensureConfigShape', 'removeDisabled', 'addDisabled', 'setEnabled'])
  vm.runInContext(extract(source, name), context)
for (const legacy of ['omadock', 'tyrsolution.app-launcher']) {
  context.config = {version: 1, plugins: [{id: legacy}]}
  const original = JSON.stringify(context.config)
  nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), false, `${legacy}: old user config defers native dock`)
  nodeAssert.strictEqual(JSON.stringify(context.config), original, 'read policy never rewrites user config')
  nodeAssert.strictEqual(context.setEnabled('omarchy.dock', true), true)
  nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), true, 'explicit opt-in enables native dock')
  assert(context.config.plugins.some(entry => entry.id === legacy), 'existing plugin identity preserved')
  assert(context.config.plugins.some(entry => entry.id === 'omarchy.dock'), 'opt-in persists as ordinary plugin entry')
  const saved = JSON.parse(JSON.stringify(context.config))
  context.config = saved
  nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), true, 'persisted opt-in survives reload')
  context.setEnabled('omarchy.dock', false)
  nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), false, 'explicit disable remains authoritative')
  context.setEnabled('omarchy.dock', true)
  nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), true, 're-enable clears disable flag and records opt-in')
}
context.config = {version: 1, plugins: []}
nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), true, 'upstream config without legacy launcher keeps native default')
context.config = {plugins: [{id: 'omadock'}, {id: 'omarchy.dock'}], disabledPlugins: ['omarchy.dock']}
nodeAssert.strictEqual(context.isEnabled('omarchy.dock'), false, 'explicit disable wins even with opt-in entry')
JS
pass "existing Maslow configs defer native dock while explicit user enable persists"
