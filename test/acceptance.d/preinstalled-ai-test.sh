#!/bin/bash

# Installed-image gate: run only in the disposable acceptance VM. This checks
# offline CLI readiness, not authentication, AI inference, or Bitwarden GUI UX.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

[[ $(uname -m) == "x86_64" ]] || fail "preinstalled AI acceptance requires the x86_64 release image"
for dependency in pacman unshare timeout readlink env date; do
  command -v "$dependency" >/dev/null || fail "preinstalled AI acceptance requires $dependency"
done

umask 077
ai_artifacts=$(mktemp -d "$ARTIFACTS/preinstalled-ai.XXXXXX")
ai_home=$(mktemp -d /tmp/maslow-ai-acceptance.XXXXXX)
trap 'rm -rf -- "$ai_home"' EXIT

# Do not inherit provider tokens, shell functions, session sockets, or the real
# user's configuration. A new network namespace has no host network access.
# Failure to establish that isolation is a failed gate, never an offline pass.
host_network=$(readlink /proc/self/ns/net)
if ! env -i PATH=/usr/bin:/bin LC_ALL=C HOME="$ai_home" \
  timeout --kill-after=5 15 unshare --user --map-root-user --net --fork \
  /bin/bash -eu -c '[[ $(readlink /proc/self/ns/net) != "$1" ]]' -- "$host_network" \
  >"$ai_artifacts/network-isolation.log" 2>&1; then
  fail "preinstalled AI network isolation unavailable" "Offline execution was NOT tested. See $ai_artifacts/network-isolation.log; enable disposable-guest user/network namespaces and retry."
fi
pass "preinstalled AI offline network isolation is available"

verify_package() {
  local tool="$1" package="$2" binary="${3:-$1}" resolved owner expected
  expected="/usr/bin/$binary"
  pacman -Q "$package" >>"$ai_artifacts/packages.txt" 2>&1 ||
    fail "$tool is genuinely preinstalled" "Required package $package is missing; no installer will run."
  resolved=$(type -P "$binary") || fail "$tool is available on the installed user PATH"
  [[ -f $expected && -x $expected && $resolved -ef $expected ]] ||
    fail "$tool resolves to its packaged executable" "A missing binary or PATH override prevents packaged readiness."
  owner=$(pacman -Qqo "$expected") || fail "$tool executable has package ownership"
  [[ $owner == "$package" ]] || fail "$tool executable belongs to $package" "Unexpected package owner: $owner"
  printf '%s\t%s\t%s\n' "$tool" "$package" "$(readlink -f "$expected")" >>"$ai_artifacts/executables.tsv"
  pass "$tool is installed and resolves to its packaged executable"
}

verify_package codex openai-codex-bin
verify_package claude claude-code
verify_package hermes hermes-agent
verify_package bitwarden bitwarden bitwarden-desktop

printf 'tool\tprobe\texit_status\telapsed_ms\n' >"$ai_artifacts/timings.tsv"
offline_probe() {
  local tool="$1" probe="$2" started finished status=0 log_file
  shift 2
  log_file="$ai_artifacts/$tool-$probe.log"
  # Each probe gets fresh state, so a successful help command cannot hide an
  # implicit initialization dependency in a later command.
  local probe_home="$ai_home/$tool-$probe"
  mkdir -p "$probe_home/config" "$probe_home/cache" "$probe_home/state" "$probe_home/data"
  started=$(date +%s%N)
  env -i PATH=/usr/bin:/bin LC_ALL=C HOME="$probe_home" \
    XDG_CONFIG_HOME="$probe_home/config" XDG_CACHE_HOME="$probe_home/cache" \
    XDG_STATE_HOME="$probe_home/state" XDG_DATA_HOME="$probe_home/data" \
    timeout --kill-after=5 60 unshare --user --map-root-user --net --fork \
    "/usr/bin/$tool" "$@" >"$log_file" 2>&1 || status=$?
  finished=$(date +%s%N)
  printf '%s\t%s\t%s\t%s\n' "$tool" "$probe" "$status" "$(((finished - started) / 1000000))" >>"$ai_artifacts/timings.tsv"
  (( status == 0 )) || fail "$tool $probe runs offline from preinstalled files" "Exit $status; see $log_file. No login or installation was requested."
  [[ -s $log_file ]] || fail "$tool $probe produces actual command output"
  pass "$tool $probe runs offline from preinstalled files"
}

verify_builtin_memory() {
  local status_text label
  status_text=$(<"$1")
  # These are the actual labels from packaged Hermes 0.21.0. Check every
  # built-in capability, not merely the heading or installed plugin metadata.
  for label in "Memory injection" "User profile" "Memory tool"; do
    grep -Eq "^[[:space:]]*$label:[[:space:]]+enabled([[:space:]]|$)" <<<"$status_text" ||
      fail "Hermes built-in $label is enabled" "See $1"
  done
  grep -Eq '^[[:space:]]*Provider:[[:space:]]*\(none — built-in only\)' <<<"$status_text" ||
    fail "Hermes fresh home uses built-in memory only" "See $1; no external provider should be configured."
}

offline_probe codex version --version
offline_probe codex help --help
offline_probe claude version --version
offline_probe claude help --help
offline_probe hermes version --version
offline_probe hermes help --help
offline_probe hermes chat-help chat --help
grep -Fq -- '--oneshot' "$ai_artifacts/hermes-chat-help.log" ||
  fail "Hermes supports the integrated interactive chat interface" "The packaged chat help lacks --oneshot; see $ai_artifacts/hermes-chat-help.log."
pass "Hermes packaged chat exposes the required interface"
offline_probe hermes memory-status memory status
verify_builtin_memory "$ai_artifacts/hermes-memory-status.log"
pass "Hermes built-in memory is enabled without an external provider"

printf '%s\n' \
  'Scope: package ownership, installed user PATH, offline CLI version/help, Hermes chat capability, and built-in memory status in fresh private homes.' \
  'Bitwarden package and PATH are checked; its GUI/sign-in is not launched by this test.' \
  'No provider authentication, agent workload, memory-provider connection, or performance parity is proven.' \
  'Elapsed times are observed probe durations, not minimum hardware requirements or comparative benchmarks.' \
  >"$ai_artifacts/scope.txt"
pass "preinstalled AI acceptance artifacts saved to $ai_artifacts"
