#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home/.local/bin" "$tmp/runtime/install/helpers" "$tmp/package-bin"
cp "$ROOT/install/helpers/agent.sh" "$tmp/runtime/install/helpers/agent.sh"
# Redirect only fixed system binary paths; exercise the real shared ownership
# and preservation logic, with no package or agent execution.
cat >>"$tmp/runtime/install/helpers/agent.sh" <<'SH'
omarchy_agent_system_command_path() { printf '%s/%s' "$TEST_PACKAGE_BIN" "$1"; }
SH
cat >"$tmp/bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
[[ $1 == "hermes-agent" && ${TEST_PACKAGE_PRESENT:-0} == 1 ]]
SH
for command in mise omarchy-install-hermes-cli hermes; do
  cat >"$tmp/bin/$command" <<'SH'
#!/bin/bash
printf '%s %s\n' "${0##*/}" "$*" >>"$TEST_CALLS"
exit 99
SH
 done
chmod +x "$tmp/bin/"*
run_migration() {
  : >"$tmp/calls"
  HOME="$tmp/home" OMARCHY_PATH="$tmp/runtime" TEST_PACKAGE_BIN="$tmp/package-bin" \
    TEST_CALLS="$tmp/calls" TEST_PACKAGE_PRESENT="${TEST_PACKAGE_PRESENT:-0}" \
    PATH="$tmp/home/.local/bin:$tmp/package-bin:$tmp/bin:$PATH" \
    bash -euo pipefail "$ROOT/migrations/1790017600.sh" >"$tmp/output" 2>&1
}

run_migration || fail "absent package leaves migration a safe no-op"
[[ ! -s $tmp/calls ]] || fail "absent package never invokes mise, installer or agent"
pass "absent packaged Hermes never bootstraps a replacement"

printf '#!/bin/bash\nexit 0\n' >"$tmp/package-bin/hermes"
chmod +x "$tmp/package-bin/hermes"
TEST_PACKAGE_PRESENT=1 run_migration || fail "installed package is preserved"
[[ ! -s $tmp/calls && ! -e $tmp/home/.local/bin/hermes ]] || fail "migration invokes a runtime or creates a wrapper"
pass "packaged Hermes migration preserves a direct package-owned command"

for kind in marker custom symlink; do
  rm -f "$tmp/home/.local/bin/hermes"
  case "$kind" in
    marker) printf '#!/bin/bash\n# Written by omarchy-install-hermes-cli.\nexit 99\n' >"$tmp/home/.local/bin/hermes" ;;
    custom) printf '#!/bin/bash\n# administrator command\nexit 99\n' >"$tmp/home/.local/bin/hermes" ;;
    symlink) ln -s "$tmp/package-bin/hermes" "$tmp/home/.local/bin/hermes" ;;
  esac
  [[ $kind == "symlink" ]] || chmod +x "$tmp/home/.local/bin/hermes"
  before=$(sha256sum "$tmp/home/.local/bin/hermes")
  TEST_PACKAGE_PRESENT=1 run_migration || fail "migration preserves $kind for explicit review"
  [[ $(sha256sum "$tmp/home/.local/bin/hermes") == "$before" && ! -s $tmp/calls ]] || fail "migration changes or executes $kind"
  [[ $kind != "symlink" || -L $tmp/home/.local/bin/hermes ]] || fail "migration replaces a user symlink"
  pass "packaged Hermes migration preserves $kind without retirement or bootstrap"
done
rm "$tmp/package-bin/hermes"
if TEST_PACKAGE_PRESENT=1 run_migration; then fail "missing package binary must leave migration pending"; fi
[[ ! -s $tmp/calls ]] || fail "incomplete package falls back to a bootstrap"
pass "incomplete packaged Hermes fails without retiring or downloading anything"
