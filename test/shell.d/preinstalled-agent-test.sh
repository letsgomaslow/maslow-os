#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const os = require('os')
const {spawnSync} = require('child_process')
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'maslow-preinstalled-test-'))
const home = path.join(tmp, 'home')
const packageBin = path.join(tmp, 'package-bin')
fs.mkdirSync(path.join(home, '.local/bin'), {recursive: true})
fs.mkdirSync(packageBin)
for (const id of ['codex', 'claude', 'hermes']) {
  fs.writeFileSync(path.join(packageBin, id), '#!/bin/bash\nexit 0\n', {mode: 0o755})
}
const helper = path.join(root, 'install/helpers/agent.sh')
const log = path.join(tmp, 'calls')
const prelude = `
source "$HELPER"
omarchy_agent_package_path() { printf '%s/%s' "$PACKAGE_BIN" "$OMARCHY_AGENT_ID"; }
omarchy-pkg-present() { [[ "$*" == "$TEST_PACKAGE" ]]; }
mise() { printf 'mise %s\\n' "$*" >>"$TEST_LOG"; return 1; }
omarchy-install-hermes-cli() { printf 'hermes %s\\n' "$*" >>"$TEST_LOG"; return 1; }
`
function run(script, extra = {}, setup = prelude) {
  return spawnSync('bash', ['-eu', '-c', setup + '\n' + script], {
    env: {...process.env, HOME: home, PATH: path.join(home, '.local/bin') + ':' + packageBin + ':' + process.env.PATH, OMARCHY_PATH: root, HELPER: helper, PACKAGE_BIN: packageBin, TEST_LOG: log, TEST_PACKAGE: 'openai-codex-bin', ...extra}, encoding: 'utf8'
  })
}
function calls() { return fs.existsSync(log) ? fs.readFileSync(log, 'utf8') : '' }
function wrapper(id) { return path.join(home, '.local/bin', id) }
function seedWrapper(id) {
  const result = spawnSync('bash', [path.join(root, 'bin/omarchy-mise-install'), id], {env: {...process.env, HOME: home}, encoding: 'utf8'})
  assertEqual(result.status, 0, 'existing upstream lazy-wrapper generator runs in isolated home')
}
try {
  for (const [id, pkg] of [['codex', 'openai-codex-bin'], ['claude', 'claude-code'], ['hermes', 'hermes-agent']]) {
    assertEqual(run(`omarchy_agent_resolve ${id}; omarchy_agent_is_installed; omarchy_agent_install_only; omarchy_agent_prepare_packaged ${id}`, {TEST_PACKAGE: pkg}).status, 0, `${id} recognizes installed package without executing it`)
    assert(!fs.existsSync(wrapper(id)), `${id} does not create a first-launch download wrapper`)
  }
  assertEqual(calls(), '', 'packaged status and install paths never invoke mise or Hermes')
  const legacyHermes = '#!/bin/bash\n# Written by omarchy-install-hermes-cli.\nexec false\n'
  fs.writeFileSync(wrapper('hermes'), legacyHermes, {mode: 0o755})
  assertEqual(run('omarchy_agent_prepare_packaged hermes', {TEST_PACKAGE: 'hermes-agent'}).status, 0, 'legacy Hermes launcher is preserved for explicit review')
  assertEqual(fs.readFileSync(wrapper('hermes'), 'utf8'), legacyHermes, 'Hermes marker alone never authorizes deletion')
  assertEqual(run('omarchy_agent_resolve hermes; omarchy_agent_is_installed', {TEST_PACKAGE: 'hermes-agent'}).status, 1, 'legacy Hermes shadow cannot claim packaged readiness')
  assertEqual(calls(), '', 'shadowed packaged Hermes never executes old readiness or installation probes')
  fs.unlinkSync(wrapper('hermes'))
  assertEqual(run('omarchy_agent_resolve codex; omarchy_agent_is_packaged', {TEST_PACKAGE: 'missing'}).status, 1, 'executable without package does not claim package ownership')
  fs.renameSync(path.join(packageBin, 'codex'), path.join(packageBin, 'codex.saved'))
  assertEqual(run('omarchy_agent_resolve codex; omarchy_agent_is_packaged').status, 1, 'package without executable is not ready')
  fs.renameSync(path.join(packageBin, 'codex.saved'), path.join(packageBin, 'codex'))

  seedWrapper('codex')
  const original = fs.readFileSync(wrapper('codex'), 'utf8')
  assertEqual(run('omarchy_agent_prepare_packaged codex').status, 0, 'known generated wrapper converts safely')
  assert(!fs.existsSync(wrapper('codex')), 'known download wrapper no longer shadows package')
  const backups = path.join(home, '.local/state/maslow-os/agent-wrapper-backups')
  const firstBackup = fs.readdirSync(backups)[0]
  assertEqual(fs.readFileSync(path.join(backups, firstBackup, 'codex'), 'utf8'), original, 'backup preserves exact original wrapper')
  assertEqual(run('omarchy_agent_prepare_packaged codex').status, 0, 'repeat finalization succeeds')
  assertEqual(fs.readdirSync(backups).length, 1, 'repeat finalization creates no redundant backup')
  seedWrapper('codex')
  assertEqual(run('omarchy_agent_prepare_packaged codex').status, 0, 'another generated wrapper converts')
  assertEqual(fs.readdirSync(backups).length, 2, 'unique backup does not overwrite previous backup')
  assertEqual(fs.readFileSync(path.join(backups, firstBackup, 'codex'), 'utf8'), original, 'older backup remains unchanged')

  fs.writeFileSync(wrapper('codex'), '#!/bin/bash\necho custom\n', {mode: 0o755})
  const custom = fs.readFileSync(wrapper('codex'), 'utf8')
  const customResult = run('omarchy_agent_prepare_packaged codex')
  assertEqual(customResult.status, 0, 'custom executable does not abort finalization')
  assert(customResult.stderr.includes('may override'), 'custom override is reported')
  assertEqual(fs.readFileSync(wrapper('codex'), 'utf8'), custom, 'custom executable remains unchanged')
  assertEqual(run('omarchy_agent_resolve codex; omarchy_agent_is_installed').status, 1, 'custom PATH override cannot claim packaged readiness')
  assertEqual(run('omarchy_agent_resolve codex; omarchy_agent_install_only').status, 1, 'package install does not falsely succeed when command is shadowed')
  assertEqual(calls(), '', 'shadowed package never falls back to network installation')
  fs.unlinkSync(wrapper('codex'))
  fs.symlinkSync(path.join(packageBin, 'codex'), wrapper('codex'))
  assertEqual(run('omarchy_agent_prepare_packaged codex').status, 0, 'user symlink is tolerated')
  assert(fs.lstatSync(wrapper('codex')).isSymbolicLink(), 'user symlink is preserved')
  assertEqual(run('omarchy_agent_resolve codex; omarchy_agent_is_installed').status, 0, 'symlink to verified packaged binary remains usable')
  fs.unlinkSync(wrapper('codex'))
  seedWrapper('codex')
  assertEqual(run('omarchy_agent_prepare_packaged codex', {TEST_PACKAGE: 'missing'}).status, 1, 'missing package cannot retire wrapper')
  assertEqual(fs.readFileSync(wrapper('codex'), 'utf8'), original, 'missing package preserves existing wrapper')
  fs.renameSync(path.join(packageBin, 'codex'), path.join(packageBin, 'codex.saved'))
  assertEqual(run('omarchy_agent_prepare_packaged codex').status, 1, 'missing packaged executable cannot retire wrapper')
  assertEqual(fs.readFileSync(wrapper('codex'), 'utf8'), original, 'missing executable preserves existing wrapper')
  fs.renameSync(path.join(packageBin, 'codex.saved'), path.join(packageBin, 'codex'))
  assertEqual(calls(), '', 'preparation never installs, removes packages, or starts an agent')

  const leaf = run('source "$OMARCHY_PATH/install/user/mise.sh"', {}, `
omarchy-pkg-present() { return 1; }
omarchy-mise-install() { printf 'stub %s\\n' "$*" >>"$TEST_LOG"; }
omarchy-install-hermes-cli() { printf 'unexpected Hermes installer\\n' >>"$TEST_LOG"; return 1; }
`)
  assertEqual(leaf.status, 0, 'user finalization tolerates missing core packages without downloads')
  assert(!calls().includes('stub codex') && !calls().includes('stub claude'), 'core tools have no lazy fallback in user finalization')
  assert(!calls().includes('unexpected Hermes installer') && !calls().includes('stub hermes'), 'user finalization never creates or probes a lazy Hermes installation')
  assert(calls().includes('stub crush\n') && calls().includes('stub github:OpenRouterLabs/ori-releases ori\n'), 'optional agent stubs retain existing behavior')
  assertEqual(fs.readFileSync(wrapper('codex'), 'utf8'), original, 'missing-package user finalization does not touch an existing executable')
  assert(fs.existsSync(path.join(packageBin, 'codex')) && fs.existsSync(path.join(packageBin, 'claude')), 'preparation leaves packaged tools installed')
  for (const pkg of ['bitwarden', 'openai-codex-bin', 'claude-code', 'hermes-agent']) {
    assert(fs.readFileSync(path.join(root, 'install/omarchy-base.packages'), 'utf8').split('\n').includes(pkg), `${pkg} belongs to the default install payload`)
  }
} finally {
  fs.rmSync(tmp, {recursive: true, force: true})
}
JS
