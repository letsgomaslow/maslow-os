#!/bin/bash

source "$(dirname "$0")/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const vm = require('vm')
const source = fs.readFileSync(path.join(root, 'shell/plugins/maslow-ai-setup/Panel.qml'), 'utf8')

// Execute the panel's actual functions and Process exit handlers. This covers
// asynchronous state transitions, not Qt rendering or process signal ordering.
const functions = [...source.matchAll(/^  function (\w+)\(([^)]*)\) \{([\s\S]*?)^  }/gm)]
const handlers = {}
for (const match of source.matchAll(/^  Process \{([\s\S]*?)^  }/gm)) {
  const id = match[1].match(/id: (\w+)/)[1]
  const exit = match[1].match(/    onExited: function\(exitCode\) \{([\s\S]*)\n    }/)
  if (exit) handlers[id] = `(function(exitCode) {${exit[1]}\n})(exitCode)`
}

// Use the panel's actual height binding with the measured footer sizes from
// Linux rendering. The previous fixed reserve placed Check again below the
// window when a two-line action message appeared.
const stepHeight = source.match(/id: setupSteps[\s\S]*?\n          height: ([\s\S]*?)\n          currentIndex:/)[1]
for (const windowHeight of [500, 620]) {
  for (const messageHeight of [0, 40, 60]) {
    const sizes = {
      parent: {height: windowHeight - 48, spacing: 18},
      productHeader: {height: 53}, progressHeader: {height: 4},
      feedbackText: {visible: messageHeight > 0, height: messageHeight},
      statusRefreshButton: {visible: true, height: 28}
    }
    const height = vm.runInNewContext(stepHeight, sizes)
    const occupied = height + 53 + 4 + 36 + 28 + 18 + (messageHeight > 0 ? messageHeight + 18 : 0)
    assert(height > 0 && occupied <= sizes.parent.height, `${windowHeight}px window keeps ${messageHeight}px feedback and refresh inside its margins`)
  }
}

// qs.Ui.Button has its own selected property. Card actions must depend on the
// selected model card rather than that unrelated button styling property.
const buttons = [...source.matchAll(/^                      Button \{([\s\S]*?)^                      }/gm)]
assertEqual(buttons.length, 3, 'all three card actions have visibility coverage')
for (const [index, button] of buttons.entries()) {
  const visible = button[1].match(/visible: ([^\n]+)/)[1]
  const data = {
    selected: false, toolCard: {selected: true}, installSupported: index === 0,
    openSupported: index !== 0, toolStatus: index === 0 ? 'selected' : 'action-required',
    setupOnly: false, prerequisiteInstalled: true, userConfirmable: false
  }
  assertEqual(vm.runInNewContext(visible, data), true, `card action ${index + 1} is visible despite the button's own selected=false`)
  data.selected = true
  data.toolCard.selected = false
  assertEqual(vm.runInNewContext(visible, data), false, `card action ${index + 1} hides when the card is deselected`)
}

function tool(id, overrides = {}) {
  return {toolId: id, adapterSupported: true, selected: false, toolStatus: 'not-started',
    setupOnly: false, userConfirmable: false, prerequisiteInstalled: false,
    openSupported: false, installSupported: true, reasonCode: '', ...overrides}
}

function panel(rows) {
  const context = {
    rows, toolModel: {count: rows.length, get: i => rows[i], setProperty: (i, key, value) => {rows[i][key] = value}},
    stateCatalogLoaded: true, stateLoaded: true, adapterCatalogLoaded: true,
    statusChecksComplete: true, statusChecksFailed: false, canFinish: false,
    busy: false, closingQueued: false, statusQueue: [], statusTool: '',
    stateWriteQueue: [], stateWriteCurrent: null, activeTool: '', activeAction: '', statusText: '',
    statusProc: {running: false}, stateWriteProc: {running: false}, actionProc: {running: false},
    toolStatusOutput: {text: ''}, closed: 0
  }
  context.root = context
  vm.createContext(context)
  for (const match of functions) vm.runInContext(`function ${match[1]}(${match[2]}) {${match[3]}\n}`, context)
  context.focusCurrentStep = () => {}
  context.requestClose = () => {context.closed++}
  context.exit = (id, code = 0) => {
    context[id].running = false
    context.exitCode = code
    vm.runInContext(handlers[id], context)
  }
  context.probe = (id, result, code = 0) => {
    context.statusTool = id
    context.toolStatusOutput.text = typeof result === 'string' ? result : JSON.stringify({
      id, supported: true, available: true, installed: false, prerequisiteInstalled: false, ...result
    })
    context.exit('statusProc', code)
  }
  return context
}

{
  const p = panel([])
  assertEqual(p.openActionLabel('codex', false, 'action-required'), 'Sign in', 'Codex keeps its separate sign-in action')
  assertEqual(p.openActionLabel('claude', false, 'action-required'), 'Sign in', 'Claude Code keeps its separate sign-in action')
  assertEqual(p.openActionLabel('hermes', false, 'action-required'), 'Launch & check', 'Hermes action does not imply provider sign-in')
  assertEqual(p.openActionLabel('hermes', false, 'needs-attention'), 'Retry', 'Hermes failures remain actionable')
  assertEqual(p.statusLabel('action-required'), 'Complete the action shown, then confirm', 'readiness requires an explicit confirmation')
  assertEqual(p.statusLabel('needs-attention'), 'Needs attention — retry available', 'failures remain explicit')
}

for (const copy of [
  'Core AI tools come with Maslow OS. Choose which ones you want to configure; sign-in happens separately in the supported tools.',
  'Start with Bitwarden for secure readiness, then choose Codex, Claude Code, or Hermes. Sign-in stays in Codex and Claude Code; Maslow OS does not inspect authentication.',
  'Ready means you completed the action shown and confirmed it; it does not prove provider authentication. Hermes uses built-in memory. External memory and MCP connections stay separate.',
  'Mark " + toolName + " ready after completing the action shown'
]) {
  assert(source.includes(copy), `onboarding copy preserves readiness and authentication boundaries: ${copy}`)
}

{
  const p = panel([])
  p.Qt = {callLater: callback => callback()}
  const viewport = {contentItem: {}, contentHeight: 802, height: 180, contentY: 360}
  p.toolsView = {contentItem: viewport}
  const card = top => ({height: 82, mapToItem: () => ({y: top})})
  p.ensureToolVisible(card(90))
  assertEqual(viewport.contentY, 90, 'Tab focus scrolls an above-viewport card into view')
  p.ensureToolVisible(card(540))
  assertEqual(viewport.contentY, 442, 'Tab focus scrolls a below-viewport card into view')
  p.ensureToolVisible(card(450))
  assertEqual(viewport.contentY, 442, 'already visible keyboard focus preserves scroll position')
  p.ensureToolVisible(card(720))
  assertEqual(viewport.contentY, 622, 'last card reveal remains within the content bounds')
}

for (const id of ['codex', 'honcho']) {
  const setupOnly = id === 'honcho'
  const p = panel([tool(id, {selected: true, toolStatus: 'ready', setupOnly, openSupported: !setupOnly, prerequisiteInstalled: true})])
  p.probe(id, {setupOnly, installed: false, prerequisiteInstalled: false})
  assertEqual(p.canFinish, false, `${id}: missing current installation/prerequisite blocks stale readiness`)
  assertEqual(p.rows[0].toolStatus, 'ready', `${id}: prior user confirmation is retained`)
  p.finishSetup()
  assertEqual(p.stateWriteCurrent.command[1], 'defer', `${id}: incomplete current setup cannot be saved as complete`)
}

{
  const p = panel([tool('honcho', {selected: true, toolStatus: 'action-required', setupOnly: true, userConfirmable: true})])
  p.markReady('honcho')
  assertEqual(p.rows[0].toolStatus, 'action-required', 'missing Hermes prevents manual memory readiness')
  p.probe('honcho', {setupOnly: true, prerequisiteInstalled: true})
  assertEqual(p.rows[0].openSupported, true, 'official memory wizard remains reopenable after its first launch')
  p.markReady('honcho')
  assertEqual(p.canFinish, true, 'memory setup can finish after prerequisite and explicit confirmation')
}

{
  const p = panel([tool('codex', {selected: true, toolStatus: 'ready', openSupported: true, installSupported: false})])
  p.toggleTool('codex', false)
  p.toggleTool('codex', true)
  assertEqual(p.rows[0].toolStatus, 'action-required', 'reselecting an installed agent exposes its sign-in action')
  assertEqual(p.canFinish, false, 'reselection does not silently confirm sign-in')
}

{
  const p = panel([tool('hermes', {selected: true, toolStatus: 'in-progress'})])
  p.activeTool = 'hermes'
  p.activeAction = 'install'
  p.busy = true
  p.exit('actionProc')
  assertDeepEqual([p.statusTool, ...p.statusQueue], ['hermes'], 'Hermes launch refreshes one authoritative prerequisite result')
  assertEqual(p.statusChecksComplete, false, 'completion waits for dependent probes')
  assertEqual(p.rows[0].toolStatus, 'selected', 'successful launcher exit does not claim installation or sign-in')
  assert(p.statusText.includes('Check again'), 'user can refresh after a detached installer finishes')
}

{
  const p = panel([tool('codex', {selected: true, installSupported: true, openSupported: false})])
  assertEqual(p.availabilityLabel('codex', false, false, false, true, false, 'selected', 'missing-core'), 'Core software missing — repair required', 'missing core software is an explicit repair state')
  assertEqual(p.primaryActionLabel('codex', false, 'selected'), 'Repair', 'missing core software never appears as a normal install')
  p.toggleTool('codex', false)
  assertEqual(p.rows[0].selected, false, 'deselect changes onboarding state without removing software')
}

for (const id of ['codex', 'hermes']) {
  const p = panel([tool(id, {selected: true})])
  p.probe(id, {installed: false, prerequisiteInstalled: false, reasonCode: 'path-shadow'})
  assertEqual(p.rows[0].installSupported, false, `${id}: a command override disables misleading repair`)
  assertEqual(p.availabilityLabel(id, false, false, false, false, false, 'selected', 'path-shadow'), 'Command override needs attention', `${id}: a command override is not called missing software`)
  p.runToolAction(id, 'install')
  assertEqual(p.actionProc.running, false, `${id}: a command override cannot launch repair`)
}

{
  const rows = [
    tool('hermes'),
    tool('memory-builtin'),
    tool('honcho'),
    tool('hindsight'),
    tool('mcp')
  ]
  const p = panel(rows)
  p.applyAdapterCatalog({tools: [
    {id: 'hermes', supported: true},
    {id: 'memory-builtin', supported: true},
    {id: 'honcho', supported: true, setupOnly: true, userConfirmable: true},
    {id: 'hindsight', supported: true, setupOnly: true, userConfirmable: true},
    {id: 'mcp', supported: true, setupOnly: true, userConfirmable: true}
  ]})
  assertDeepEqual([p.statusTool, ...p.statusQueue], ['hermes'], 'one Hermes probe supplies every dependent prerequisite')
  p.probe('hermes', {installed: true, prerequisiteInstalled: true})
  for (const id of ['memory-builtin', 'honcho', 'hindsight', 'mcp'])
    assertEqual(rows.find(row => row.toolId === id).prerequisiteInstalled, true, `${id}: fresh Hermes result enables configuration`)
}

{
  const p = panel([tool('honcho', {selected: true, setupOnly: true, userConfirmable: true, prerequisiteInstalled: true})])
  p.activeTool = 'honcho'
  p.activeAction = 'install'
  p.exit('actionProc')
  assertEqual(p.rows[0].toolStatus, 'action-required', 'wizard launch still requires explicit user confirmation')
  assert(!p.statusText.includes('closed'), 'launcher exit never claims that the official wizard closed')
}

for (const invalid of ['{', '{}', JSON.stringify({id: 'claude', supported: true, available: true, installed: true, prerequisiteInstalled: true})]) {
  const p = panel([tool('codex')])
  p.probe('codex', invalid)
  assertEqual(p.statusChecksFailed, true, 'invalid or mismatched status is a failed probe')
  assertEqual(p.canFinish, false, 'invalid status prevents completion')
}

{
  const p = panel([tool('codex')])
  p.probe('codex', {}, 1)
  assertEqual(p.canFinish, false, 'failed status command prevents completion')
  p.statusChecksFailed = false
  p.probe('codex', {installed: true, prerequisiteInstalled: true})
  assertEqual(p.rows[0].selected, false, 'installation status does not select a tool for the user')
  assertEqual(p.rows[0].toolStatus, 'not-started', 'unselected installed tool stays unconfigured')
  p.toggleTool('codex', true)
  assertEqual(p.rows[0].toolStatus, 'action-required', 'selecting an installed tool requires explicit sign-in confirmation')
}

{
  const p = panel([tool('codex')])
  p.toggleTool('codex', true)
  p.saveStep(3)
  p.deferSetup()
  p.toggleTool('codex', false)
  assertEqual(p.rows[0].selected, true, 'queued closure freezes further selections')
  const commands = []
  while (p.stateWriteCurrent) {
    commands.push(p.stateWriteCurrent.command[1])
    p.exit('stateWriteProc')
  }
  assertDeepEqual(commands, ['tool-select', 'step', 'defer'], 'rapid writes persist in order before closing')
  assertEqual(p.closed, 1, 'panel closes once after the final write succeeds')
}

{
  const p = panel([tool('codex', {installSupported: true})])
  p.runToolAction('codex', 'install')
  assertEqual(p.actionProc.running, false, 'installation waits for its progress write')
  p.exit('stateWriteProc', 1)
  assertEqual(p.actionProc.running, false, 'failed state write never launches installation')
  assertEqual(p.busy, false, 'failed state write permits retry')
  assertEqual(p.stateWriteQueue.length, 0, 'failed state write clears dependent writes')
}

{
  const p = panel([tool('codex')])
  p.runToolAction('codex', 'install')
  p.exit('stateWriteProc')
  assertDeepEqual(p.actionProc.command, ['omarchy-setup-ai-tool', 'install', 'codex'], 'saved progress launches exactly the selected adapter')
  p.exit('actionProc', 130)
  assertEqual(p.rows[0].toolStatus, 'selected', 'canceled launcher retains selection for retry')
}
JS
