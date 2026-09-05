#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

require_command jq

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

if "$ROOT/bin/omarchy-debug-performance" --settle=-1 --sample=1 >"$test_tmp/invalid.out" 2>&1; then
  fail "performance baseline accepts a negative settle time"
fi
if "$ROOT/bin/omarchy-debug-performance" --settle=0 --sample=0 >"$test_tmp/invalid.out" 2>&1; then
  fail "performance baseline accepts a zero CPU sample"
fi
pass "performance baseline rejects invalid sampling windows"

grep -Fq 'Cold boot, login-to-desktop, and application-launch timings require an external observer' "$ROOT/docs/performance-baseline.md" || fail "performance guide does not preserve the launch-timing boundary"
grep -Fq 'ISO size and installer phase timing belong to `letsgomaslow/maslow-os-iso`' "$ROOT/docs/performance-baseline.md" || fail "performance guide does not route ISO timing to its owning repository"
pass "performance guide keeps runtime, launch, package, and ISO evidence separate"

run_node_test <<'JS'
const fs = require('fs')
const {spawnSync} = require('child_process')
const source = fs.readFileSync(path.join(root, 'bin/omarchy-debug-performance'), 'utf8')
assert(source.includes('--arg host "$(uname -n)"') && !source.includes('$(hostname)'), 'host capture uses coreutils uname without optional hostname package')
const program = source.match(/read_cpu\(\) \{\n  awk '([\s\S]*?)' \/proc\/stat/)[1]
for (const [input, expected] of [
  ['cpu 100 20 30 200 10 4 6 8 40 3\n', '210 378'],
  ['cpu 100 20 30 200\n', '200 350']
]) {
  const result = spawnSync('awk', [program], {input, encoding: 'utf8'})
  assertEqual(result.status, 0, 'CPU accounting fixture executes')
  assertEqual(result.stdout.trim(), expected, 'CPU total counts guest time once and supports shorter records')
}
const collectors = source.slice(source.indexOf('collect_units() {'), source.indexOf('\nenabled_user_units='))
const fixture = `
systemctl() {
  printf '%s\\n' 'quickshell.service loaded active running' 'maslow-orca.service loaded active running'
}
ps() {
  if [[ "$*" != '-e -o pid=,uid=,rss=,%cpu=,comm=' ]]; then
    echo 'SECRET_ARGV_MUST_NOT_BE_READ'
    return 1
  fi
  printf '%s\\n' ' 11 1000 12000 1.2 quickshell' ' 12 1000 3000 0.0 orca' ' 13 0 1000 0.1 name with spaces'
}
`
function collect(command, mock = fixture) {
  const result = spawnSync('bash', ['-c', collectors + '\n' + mock + '\n' + command], {encoding: 'utf8'})
  assertEqual(result.status, 0, 'snapshot collector executes')
  return JSON.parse(result.stdout)
}
const processes = collect('collect_processes')
assertEqual(processes.available, true, 'process snapshot marks successful collection')
assertEqual(processes.processes.map(p => p.command).join('|'), 'quickshell|orca|name with spaces', 'ordinary names and other users are not filtered out')
assertEqual(processes.processes[0].rssKiB, 12000, 'RSS remains numeric')
assertEqual(Object.keys(processes.processes[0]).sort().join(','), 'command,cpuPercent,pid,rssKiB,uid', 'process snapshot contains names and metrics, never argv')
assertEqual(collect('collect_units --user list-units').names.join('|'), 'maslow-orca.service|quickshell.service', 'shared service names remain visible')
assertEqual(collect('collect_processes', 'ps() { return 1; }').available, false, 'failed process collection is unavailable, not empty success')
assertEqual(collect('collect_units --user list-units', 'systemctl() { return 1; }').available, false, 'unavailable systemd is explicit')
JS

if [[ ! -r /proc/meminfo || ! -r /proc/stat ]]; then
  pass "Linux procfs unavailable; skipping performance baseline runtime test"
  exit 0
fi

mkdir -p "$test_tmp/bin"
cat >"$test_tmp/bin/systemctl" <<'SH'
#!/bin/bash
printf '%s\n' maslow-helper.service unrelated.service maslow-watch.path
SH
chmod +x "$test_tmp/bin/systemctl"

output=$(PATH="$test_tmp/bin:$PATH" "$ROOT/bin/omarchy-debug-performance" --json --settle=0 --sample=1)

[[ $(jq -r '.schemaVersion' <<<"$output") == 1 ]] || fail "performance baseline schema is not versioned"
[[ $(jq -r '.purpose' <<<"$output") == engineering-evidence ]] || fail "performance baseline is not labeled as engineering evidence"
[[ $(jq -r '.note | contains("not minimum system requirements")' <<<"$output") == true ]] || fail "performance baseline can be mistaken for minimum requirements"
jq -e '.idle.memoryUsedKiB > 0 and .idle.memoryTotalKiB > .idle.memoryUsedKiB' <<<"$output" >/dev/null || fail "performance baseline does not report plausible memory values"
jq -e '.idle.cpuPercent == null or (.idle.cpuPercent >= 0 and .idle.cpuPercent <= 100)' <<<"$output" >/dev/null || fail "performance baseline CPU sample is outside its valid range"
[[ $(jq -r '.maslowNamedUserServices | join(" ")' <<<"$output") == "maslow-helper.service maslow-watch.path" ]] || fail "performance baseline does not limit enabled services to Maslow names"
jq -e '.maslowNamedProcesses | type == "array"' <<<"$output" >/dev/null || fail "performance baseline process result is not structured"
jq -e '.enabledUserUnits.available and (.enabledUserUnits.names | index("unrelated.service") != null) and .processSnapshot.available and (.processSnapshot.processes | length > 0)' <<<"$output" >/dev/null || fail "performance baseline omits non-Maslow attribution"
pass "performance baseline emits comparable read-only engineering evidence"

cat >"$test_tmp/bin/systemctl" <<'SH'
#!/bin/bash
exit 1
SH
output=$(PATH="$test_tmp/bin:$PATH" "$ROOT/bin/omarchy-debug-performance" --json --settle=0 --sample=1)
jq -e '.maslowNamedUserServices == [] and .idle.memoryUsedKiB > 0' <<<"$output" >/dev/null || fail "unavailable user systemd manager aborts or corrupts the performance baseline"
jq -e '(.enabledUserUnits.available == false) and (.runningUserServices.available == false) and (.runningSystemServices.available == false)' <<<"$output" >/dev/null || fail "unavailable systemd is indistinguishable from no services"
pass "performance baseline tolerates an unavailable user systemd manager"
