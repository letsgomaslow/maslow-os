#!/bin/bash

source "$(dirname "${BASH_SOURCE[0]}")/base-test.sh"

migration=$(grep -rl 'Refresh Maslow OS theme artwork' "$ROOT/migrations" | head -n 1 || true)
[[ -n $migration ]] || fail "Maslow theme artwork migration exists"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
refresh_log="$test_tmp/theme-refresh.log"
mkdir -p "$mock_bin"

printf '#!/bin/bash\nprintf "%%s\\n" "$HOME" >>"%s"\n' "$refresh_log" >"$mock_bin/omarchy-theme-refresh"
chmod +x "$mock_bin/omarchy-theme-refresh"

run_migration() {
  local home=$1 theme=${2:-}

  if [[ -n $theme ]]; then
    mkdir -p "$home/.local/state/omarchy/current"
    printf '%s\n' "$theme" >"$home/.local/state/omarchy/current/theme.name"
  fi

  HOME="$home" OMARCHY_PATH="$ROOT" PATH="$mock_bin:$PATH" bash -euo pipefail "$migration" >/dev/null
}

run_migration "$test_tmp/dark" "maslow-dark"
run_migration "$test_tmp/light" "maslow-light"

(( $(wc -l <"$refresh_log") == 2 )) || fail "migration refreshes both Maslow themes"
pass "migration refreshes both Maslow themes"

run_migration "$test_tmp/upstream" "tokyo-night"
run_migration "$test_tmp/missing"

(( $(wc -l <"$refresh_log") == 2 )) || fail "migration leaves other and unset themes unchanged"
pass "migration leaves other and unset themes unchanged"
