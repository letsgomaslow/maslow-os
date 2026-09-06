#!/bin/bash

source "$(dirname "$0")/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const vm = require('vm')
const source = fs.readFileSync(path.join(root, 'shell/plugins/maslow-ai-setup/Panel.qml'), 'utf8')

function balancedBlock(text, braceStart) {
  let depth = 0
  let quote = ''
  let escaped = false
  for (let index = braceStart; index < text.length; index++) {
    const char = text[index]
    if (quote) {
      if (escaped) escaped = false
      else if (char === '\\') escaped = true
      else if (char === quote) quote = ''
      continue
    }
    if (char === '"' || char === "'" || char === '`') { quote = char; continue }
    if (char === '{') depth++
    if (char === '}' && --depth === 0) return text.slice(braceStart + 1, index)
  }
  throw new Error('unclosed QML block')
}

function panelFunction(name) {
  const match = new RegExp(`function ${name}\\(([^)]*)\\)\\s*\\{`).exec(source)
  if (!match) throw new Error(`missing function ${name}`)
  const start = match.index + match[0].lastIndexOf('{')
  return `function ${name}(${match[1]}) {${balancedBlock(source, start)}}`
}

function processHandler(id) {
  const marker = `id: ${id}`
  const idOffset = source.indexOf(marker)
  if (idOffset < 0) throw new Error(`missing process ${id}`)
  const handlerOffset = source.indexOf('onExited: function(exitCode)', idOffset)
  if (handlerOffset < 0) throw new Error(`missing exit handler ${id}`)
  const braceStart = source.indexOf('{', handlerOffset)
  return `(function(exitCode) {${balancedBlock(source, braceStart)}})(exitCode)`
}

function row(id, overrides = {}) {
  return {
    toolId: id, toolName: id, supported: true, available: true, installed: false,
    desktopInstalled: false, runtimeState: 'none', authentication: 'unknown',
    runtimeOwner: 'none', checkAvailable: false, reasonCode: '', history: 'not-started',
    ...overrides
  }
}

function makePanel(rows = []) {
  const context = {
    rows,
    window: {visible: true},
    focusCurrentStep: () => {},
    startStatusChecks: () => {},
    toolModel: {
      get count() { return rows.length },
      append: item => rows.push(item),
      get: index => rows[index],
      setProperty: (index, key, value) => { rows[index][key] = value }
    },
    stateCatalogLoaded: true,
    stateLoaded: true,
    adapterCatalogLoaded: true,
    closingQueued: false,
    busy: false,
    statusText: '',
    statusQueue: [],
    stateWriteQueue: [],
    stateWriteCurrent: null,
    accountChoice: '',
    accountAuthentication: 'unknown',
    hermesChoice: 'recommended',
    hermesOperational: 'unverified',
    hermesOwner: 'none',
    hermesCheckAvailable: false,
    memoryChoice: 'builtin',
    memoryConfirmed: true,
    memoryExpanded: false,
    desktopChoice: 'none',
    runGeneration: 1,
    statusProcessGeneration: 1,
    checkProcessGeneration: 1,
    actionProcessGeneration: 1,
    activeTool: '',
    activeAction: '',
    closed: 0,
    statusProc: {running: false, signal: () => {}},
    hermesCheckProc: {running: false, signal: () => {}},
    actionRefresh: {restart: () => {}, stop: () => {}},
    actionProc: {running: false, startDetached: () => {context.detached = true}},
    stateWriteProc: {running: false},
    toolStatusOutput: {text: ''},
    hermesCheckOutput: {text: ''}
  }
  context.root = context
  vm.createContext(context)
  for (const name of [
    'findTool', 'tool', 'statusFor', 'accountProofSufficient', 'hermesProofSufficient',
    'memoryChoiceValid', 'desktopChoiceReady', 'legacyProgressIncomplete', 'completeEligible', 'choiceValue',
    'applyToolStatus', 'applyAdapterCatalog', 'applyState', 'invalidateStatus', 'canRunToolAction', 'queueStateWrite', 'startNextStateWrite', 'runToolAction',
    'desktopStateLabel', 'desktopActionLabel', 'checkHermes', 'finishForNow', 'resetSetup', 'checkNextStatus'
  ]) vm.runInContext(panelFunction(name), context)
  context.requestClose = () => { context.closed++ }
  context.cancelReadOnlyChecks = () => { context.statusQueue = [] }
  context.exit = (id, code = 0) => {
    context[id].running = false
    context.exitCode = code
    vm.runInContext(processHandler(id), context)
  }
  return context
}

{
  const p = makePanel([row('codex'), row('hermes')])
  p.accountChoice = 'codex'
  p.applyToolStatus({schemaVersion: 1, id: 'codex', supported: true, available: true, installed: true, authentication: 'signed-in', runtimeOwner: 'packaged'})
  p.hermesChoice = 'deferred'
  assertEqual(p.completeEligible(), true, 'one signed-in coding account and deferred Hermes can complete')
}

{
  const p = makePanel([row('codex', {history: 'ready'})])
  p.accountChoice = 'codex'
  p.hermesChoice = 'deferred'
  assertEqual(p.completeEligible(), false, 'historical ready never becomes current authentication proof')
}

{
  const p = makePanel([row('codex')])
  p.accountChoice = 'codex'
  p.accountAuthentication = 'signed-in'
  p.hermesChoice = 'deferred'
  p.memoryChoice = 'honcho'
  p.memoryConfirmed = false
  assertEqual(p.completeEligible(), false, 'external memory blocks completion until the user confirms its wizard')
  p.memoryConfirmed = true
  assertEqual(p.completeEligible(), true, 'external memory may complete after explicit user confirmation')
}

{
  const p = makePanel([row('hermes', {runtimeOwner: 'packaged', installed: true, checkAvailable: true})])
  p.hermesOperational = 'ready'
  p.applyToolStatus({schemaVersion: 1, id: 'hermes', supported: true, available: true, installed: true, authentication: 'unknown', runtimeOwner: 'desktop', checkAvailable: false})
  assertEqual(p.hermesOperational, 'unverified', 'a changed Hermes runtime owner invalidates earlier operational proof')
}

{
  const p = makePanel([row('codex', {installed: true, available: false})])
  p.runToolAction('codex', 'launch')
  assertEqual(p.actionProc.running, false, 'actions wait for progress to save')
  p.exit('stateWriteProc')
  assertEqual(p.detached, true, 'an installed offline tool launches detached from onboarding lifetime')
  assertDeepEqual(p.actionProc.command, ['omarchy-setup-ai-tool', 'launch', 'codex'], 'installed offline tool uses the plain interactive launch action')
}

{
  const p = makePanel([row('codex', {available: true, installed: false, runtimeOwner: 'foreign', reasonCode: 'path-shadow'})])
  p.runToolAction('codex', 'install')
  assertEqual(p.actionProc.running, false, 'a foreign command never offers a misleading repair')
}

{
  const p = makePanel([row('hermes', {installed: true, checkAvailable: false})])
  p.checkHermes()
  assertEqual(p.hermesCheckProc.running, false, 'unavailable Hermes checks never run a request')
  assertEqual(p.hermesOperational, 'unavailable', 'unavailable Hermes checks guide rather than fabricate success')
}

{
  const p = makePanel([row('codex', {history: 'selected'})])
  p.finishForNow()
  assertDeepEqual(p.stateWriteCurrent.command, ['omarchy-setup-ai-state', 'defer'], 'Finish for now queues only defer')
  p.stateWriteQueue = [{command: ['omarchy-setup-ai-state', 'choice', 'account', 'codex']}]
  p.exit('stateWriteProc', 1)
  assertEqual(p.closed, 0, 'a failed state write never closes the setup flow')
  assertEqual(p.stateWriteQueue.length, 0, 'a failed state write discards dependent queued writes')
}

{
  const p = makePanel([row('codex', {history: 'selected'})])
  p.resetSetup()
  assertEqual(p.accountChoice, '', 'reset clears in-memory account choice before a later reopen')
  assertEqual(p.memoryChoice, 'builtin', 'reset restores built-in memory preference')
  assertEqual(p.rows[0].history, 'not-started', 'reset clears historical progress shown by this panel')
  assertEqual(p.runGeneration, 2, 'reset invalidates outstanding asynchronous callbacks')
}

{
  const p = makePanel([row('codex')])
  p.statusText = 'fresh panel state'
  p.runGeneration = 2
  p.statusProcessGeneration = 1
  p.exit('statusProc', 1)
  assertEqual(p.statusText, 'fresh panel state', 'stale status exit cannot overwrite a reopened panel')
}

{
  const p = makePanel([row('codex')])
  p.applyAdapterCatalog({tools: [{id: 'hermes-desktop', name: 'Hermes Desktop', supported: true}, {id: 'chatgpt-desktop', name: 'ChatGPT Desktop', supported: true}]})
  assertEqual(p.toolModel.count, 3, 'desktop capabilities are added independently of the legacy persistence catalog')
  p.applyState({setupChoices: {memory: 'honcho'}, tools: {}})
  assertEqual(p.memoryConfirmed, false, 'resumed external memory is not silently confirmed')
}
{
  const p = makePanel([row('codex', {installed: true})])
  p.runToolAction('codex', 'open')
  p.exit('stateWriteProc', 1)
  assertEqual(p.detached, undefined, 'failed progress write cannot launch a dependent login')
}
{
  const p = makePanel([row('codex')])
  p.accountChoice = 'codex'
  p.accountAuthentication = 'signed-in'
  p.statusTool = 'codex'
  p.exit('statusProc', 1)
  assertEqual(p.accountAuthentication, 'unknown', 'a failed refresh invalidates old sign-in evidence')
  p.hermesCheckOutput.text = JSON.stringify({schemaVersion: 1, id: 'hermes', operational: 'ready'})
  p.exit('hermesCheckProc', 1)
  assertEqual(p.hermesOperational, 'failed', 'a failed process cannot smuggle a ready response')
}

{
  const p = makePanel([row('codex'), row('chatgpt-desktop', {runtimeState: 'preparing'})])
  p.accountChoice = 'codex'; p.accountAuthentication = 'signed-in'; p.hermesChoice = 'deferred'
  p.desktopChoice = 'chatgpt-desktop'
  assertEqual(p.completeEligible(), false, 'selected desktop preparation cannot be completed prematurely')
  p.rows[1].runtimeState = 'ready'
  assertEqual(p.completeEligible(), true, 'ready optional desktop can complete with the connected account')
  p.invalidateStatus('chatgpt-desktop')
  assertEqual(p.completeEligible(), false, 'failed desktop refresh revokes stale readiness')
}
{
  const desktop = row('hermes-desktop', {desktopInstalled: true, runtimeState: 'attention', runtimeOwner: 'foreign'})
  const p = makePanel([desktop])
  assertEqual(p.desktopStateLabel(desktop), 'Needs attention', 'unverified bootstrap never claims active preparation')
  assertEqual(p.desktopActionLabel(desktop), 'Open setup', 'incomplete desktop directs users into app recovery')
  assertEqual(p.canRunToolAction(desktop, 'open'), true, 'fixed packaged desktop remains a recovery path despite foreign CLI')
  assertEqual(p.canRunToolAction(row('hermes', {runtimeOwner: 'foreign'}), 'launch'), false, 'foreign CLI is still blocked')
}
for (const requirement of [
  'Your AI.\\nReady to work.',
  'Layout.maximumWidth: 1040',
  'path: Quickshell.env("HOME") + "/.local/state/omarchy/toggles/hypr/reduced-motion.lua"',
  'duration: root.reducedMotion ? 0 : 260',
  'focusable: true',
  'Customize setup',
  'desktopInstalled',
  'Qt.rgba(foreground.r, foreground.g, foreground.b, 0.74)',
  'color: quiet ? "transparent" : root.foreground',
  'minimumSize: Qt.size(600, 480)'
]) assert(source.includes(requirement), `panel source retains required UI contract: ${requirement}`)

assert(!source.includes('"tool-status", toolId, "ready"'), 'panel never persists proof-like ready status')
assert(!source.includes('actionProc.signal(15)'), 'close and reset never cancel installers or launchers')
assert(!source.includes('--yolo') && !source.includes('--auto'), 'panel never adds automatic approval flags')
JS
