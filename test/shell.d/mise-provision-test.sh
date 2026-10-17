#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT
mock_bin="$test_tmp/bin"
export HOME="$test_tmp/home with spaces"
export PATH="$mock_bin:$HOME/.local/bin:$ROOT/bin:/usr/local/bin:/usr/bin"
export OMARCHY_PATH="$ROOT"
export OMARCHY_TEST_MISE_LOG="$test_tmp/mise-log"
mkdir -p "$mock_bin" "$HOME/.local/bin"
cat >"$mock_bin/mise" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >>"$OMARCHY_TEST_MISE_LOG"
SH
cat >"$mock_bin/omarchy-pkg-present" <<'SH'
#!/bin/bash
exit 1
SH
chmod +x "$mock_bin/"*

source "$ROOT/install/user/mise.sh"
mapfile -d '' -t args <"$OMARCHY_TEST_MISE_LOG"
[[ ${args[*]} == "settings set upgrade.auto_prune false reshim" ]] ||
  fail "provisioning configures retention and reshims without downloading agents"
for agent in codex claude hermes kimi cursor-agent muse; do
  [[ ! -e $HOME/.local/bin/$agent ]] || fail "provisioning does not replace packaged or deferred $agent with a lazy wrapper"
done
[[ -x $HOME/.local/bin/opencode && -x $HOME/.local/bin/gh ]] || fail "existing optional tools retain their lazy wrappers"
pass "provisioning preserves packaged-agent ownership and defers new agent catalog entries"

for agent in codex claude hermes kimi cursor-agent muse; do
  launcher="$HOME/.local/bin/$agent"
  for kind in script binary symlink; do
    rm -f "$launcher"
    case $kind in
      script) printf '#!/bin/bash\necho user-managed command\n' >"$launcher" ;;
      binary) cp /usr/bin/true "$launcher" ;;
      symlink) ln -s /usr/bin/true "$launcher" ;;
    esac
    [[ $kind == "symlink" ]] || chmod +x "$launcher"
    cp -P "$launcher" "$test_tmp/original"
    for attempt in 1 2; do
      source "$ROOT/install/user/mise.sh"
      if [[ $kind == "symlink" ]]; then
        [[ -L $launcher && $(readlink "$launcher") == /usr/bin/true ]] || fail "provisioning preserves the $agent symlink"
      else
        [[ ! -L $launcher ]] && cmp -s "$launcher" "$test_tmp/original" || fail "provisioning preserves the $agent $kind"
      fi
    done
    rm -f "$test_tmp/original"
    pass "provisioning preserves the $agent $kind on repeated runs"
  done
done
