#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/package-bin" "$tmp/home/.local/bin" "$tmp/runtime/install/helpers"
cp "$ROOT/install/helpers/agent.sh" "$tmp/runtime/install/helpers/agent.sh"
cat >>"$tmp/runtime/install/helpers/agent.sh" <<'SH'
omarchy_agent_system_command_path() { printf '%s/%s' "$TEST_PACKAGE_BIN" "$1"; }
SH
for helper in omarchy-pkg-available omarchy-pkg-add omarchy-install-hermes-cli setsid; do
  cat >"$tmp/bin/$helper" <<'SH'
#!/bin/bash
printf '%s %s\n' "${0##*/}" "$*" >>"$TEST_CALLS"
case "${0##*/}" in
  omarchy-pkg-available) [[ ${TEST_DESKTOP_AVAILABLE:-1} == 1 ]] ;;
  omarchy-pkg-add) [[ ${TEST_INSTALL_FAIL:-0} == 0 ]] ;;
  setsid) touch "$TEST_LAUNCHED" ;;
  *) exit 99 ;;
esac
SH
 done
cat >"$tmp/bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
case "$1" in
  hermes-agent) [[ ${TEST_PACKAGE_PRESENT:-1} == 1 ]] ;;
  hermes-desktop) [[ ${TEST_DESKTOP_PRESENT:-1} == 1 ]] ;;
  *) exit 1 ;;
esac
SH
cat >"$tmp/bin/mise" <<'SH'
#!/bin/bash
printf 'unexpected mise %s\n' "$*" >>"$TEST_CALLS"
exit 99
SH
printf '#!/bin/bash\nprintf "unexpected package execution\\n" >>"$TEST_CALLS"\nexit 99\n' >"$tmp/package-bin/hermes"
chmod +x "$tmp/bin/"* "$tmp/package-bin/hermes"
run() {
  HOME="$tmp/home" OMARCHY_PATH="$tmp/runtime" TEST_CALLS="$tmp/calls" TEST_LAUNCHED="$tmp/launched" \
    TEST_PACKAGE_BIN="$tmp/package-bin" TEST_DESKTOP_AVAILABLE="${TEST_DESKTOP_AVAILABLE:-1}" \
    TEST_PACKAGE_PRESENT="${TEST_PACKAGE_PRESENT:-1}" TEST_DESKTOP_PRESENT="${TEST_DESKTOP_PRESENT:-1}" \
    TEST_INSTALL_FAIL="${TEST_INSTALL_FAIL:-0}" PATH="$tmp/home/.local/bin:$tmp/package-bin:$tmp/bin:$PATH" \
    bash "$ROOT/bin/$1" "${@:2}" >"$tmp/output" 2>&1
}
reset_calls() { : >"$tmp/calls"; rm -f "$tmp/launched"; }
wait_launch() {
  for _ in {1..50}; do [[ -e $tmp/launched ]] && return 0; sleep .01; done
  return 1
}

reset_calls
TEST_DESKTOP_AVAILABLE=0 run omarchy-install-ai-hermes && fail "unavailable Desktop must refuse before installation"
[[ $(wc -l <"$tmp/calls") == 1 && ! -e $tmp/launched ]] || fail "unavailable Desktop changes package or launch state"
pass "unavailable Hermes Desktop refuses before package mutation"
reset_calls
TEST_INSTALL_FAIL=1 run omarchy-install-ai-hermes && fail "failed Desktop install must propagate failure"
[[ ! -e $tmp/launched ]] || fail "failed package install still opens Desktop"
pass "Hermes Desktop package failure prevents launch"

for state in absent custom; do
  rm -f "$tmp/home/.local/bin/hermes"
  if [[ $state == "custom" ]]; then
    printf '#!/bin/bash\n# manual Hermes\nexit 99\n' >"$tmp/home/.local/bin/hermes"
    chmod +x "$tmp/home/.local/bin/hermes"
    before=$(sha256sum "$tmp/home/.local/bin/hermes")
  fi
  reset_calls
  run omarchy-install-ai-hermes || fail "Desktop package installation succeeds with $state CLI override"
  wait_launch || fail "explicit Desktop install opens its fixed application"
  grep -qx 'omarchy-pkg-add hermes-desktop' "$tmp/calls" || fail "Desktop installs only its fixed package"
  ! grep -Eq 'omarchy-install-hermes-cli|unexpected|curl|mise' "$tmp/calls" || fail "Desktop installation retires, probes or bootstraps CLI"
  if [[ $state == "custom" ]]; then
    [[ $(sha256sum "$tmp/home/.local/bin/hermes") == "$before" ]] || fail "Desktop modifies manual CLI"
  else
    [[ ! -e $tmp/home/.local/bin/hermes ]] || fail "Desktop creates a competing CLI"
  fi
  pass "explicit Desktop installation preserves $state CLI without installer bootstrap"
done

rm -f "$tmp/home/.local/bin/hermes"
for mode in --check --now ''; do
  reset_calls
  run omarchy-install-hermes-cli ${mode:+"$mode"} || fail "packaged CLI mode $mode uses direct package readiness"
  [[ ! -s $tmp/calls && ! -e $tmp/home/.local/bin/hermes ]] || fail "packaged CLI mode executes, bootstraps or creates a wrapper"
done
pass "packaged CLI with Desktop installed remains non-executing and package-owned"

printf '#!/bin/bash\n# Written by omarchy-install-hermes-cli.\nexit 99\n' >"$tmp/home/.local/bin/hermes"
chmod +x "$tmp/home/.local/bin/hermes"
reset_calls
run omarchy-install-hermes-cli --owns || fail "exact legacy wrapper retains its owns contract"
if run omarchy-install-hermes-cli --check; then fail "shadowed package cannot claim readiness"; fi
before=$(sha256sum "$tmp/home/.local/bin/hermes")
if run omarchy-install-hermes-cli --now; then fail "shadowed package must require explicit review"; fi
[[ $(sha256sum "$tmp/home/.local/bin/hermes") == "$before" && ! -s $tmp/calls ]] || fail "packaged fallback removes or executes a legacy wrapper"
printf '#!/bin/bash\n# manual command\nexit 99\n' >"$tmp/home/.local/bin/hermes"
if run omarchy-install-hermes-cli --owns; then fail "package presence must not claim a foreign wrapper"; fi
[[ ! -s $tmp/calls ]] || fail "owns executes or bootstraps a runtime"
pass "packaged CLI preserves owns semantics and refuses shadowed readiness"
