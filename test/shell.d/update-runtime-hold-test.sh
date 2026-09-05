#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mkdir -p "$test_tmp/bin" "$test_tmp/upstream" "$test_tmp/home"
product_file="$test_tmp/product.json"
printf '%s\n' '{"product":{"id":"maslow-os"}}' >"$product_file"
log_file="$test_tmp/pacman.log"

cat >"$test_tmp/bin/sudo" <<'STUB'
#!/bin/bash
unset MASLOW_ALLOW_RUNTIME_UPDATE
exec "$@"
STUB
cat >"$test_tmp/bin/env-probe" <<'STUB'
#!/bin/bash
printf '%s\n' "${MASLOW_ALLOW_RUNTIME_UPDATE:-unset}"
STUB
cat >"$test_tmp/bin/pacman" <<'STUB'
#!/bin/bash
printf '%s\n' "$*" >>"$TEST_LOG"
STUB
cat >"$test_tmp/bin/omarchy-hook" <<'STUB'
#!/bin/bash
exit 0
STUB
cat >"$test_tmp/bin/omarchy-update-system-pkgs-when-conflicted" <<'STUB'
#!/bin/bash
exit 99
STUB
chmod +x "$test_tmp/bin/"*

run_maslow() {
  MASLOW_PRODUCT_FILE="$product_file" OMARCHY_PATH="$ROOT" HOME="$test_tmp/home" TEST_LOG="$log_file" PATH="$test_tmp/bin:$ROOT/bin:$PATH" "$@"
}

hold_args=()
while IFS= read -r arg; do
  hold_args+=("$arg")
done < <(run_maslow omarchy-update-runtime-guard pacman-args)
[[ ${hold_args[*]} == "--ignore omarchy,omarchy-settings,omarchy-dev,omarchy-settings-dev" ]] || fail "Maslow hold does not name only runtime packages"
pass "Maslow hold targets only runtime and settings packages"

if run_maslow omarchy-update-runtime-guard >"$test_tmp/out" 2>"$test_tmp/err"; then
  fail "Maslow package transaction guard allows runtime replacement"
fi
grep -q 'dependencies will continue to update' "$test_tmp/err" || fail "runtime hold does not explain dependency updates"
grep -q 'eventually cause incompatibilities' "$test_tmp/err" || fail "runtime hold hides partial-upgrade risk"
MASLOW_ALLOW_RUNTIME_UPDATE=1 run_maslow omarchy-update-runtime-guard
pass "Maslow package transaction guard requires an explicit reviewed override"

[[ $(MASLOW_ALLOW_RUNTIME_UPDATE=1 "$test_tmp/bin/sudo" "$test_tmp/bin/env-probe") == "unset" ]] || fail "sudo fixture preserves an unapproved inherited runtime override"
[[ $(MASLOW_ALLOW_RUNTIME_UPDATE=1 "$test_tmp/bin/sudo" env MASLOW_ALLOW_RUNTIME_UPDATE=1 "$test_tmp/bin/env-probe") == 1 ]] || fail "reviewed sudo env recovery cannot pass the explicit runtime override"
pass "sudo fixture drops inherited overrides and preserves only explicit sudo env recovery"

if MASLOW_ALLOW_RUNTIME_UPDATE=1 run_maslow omarchy-channel-set stable >"$test_tmp/out" 2>"$test_tmp/err"; then
  fail "runtime override enables a Maslow channel switch"
fi
pass "runtime override remains scoped away from channel and dev-link switching"

: >"$log_file"
run_maslow bash "$ROOT/bin/omarchy-update-system-pkgs"
grep -Fx -- '-Syu --noconfirm --ignore omarchy,omarchy-settings,omarchy-dev,omarchy-settings-dev --overwrite /usr/share/omarchy/*' "$log_file" >/dev/null || fail "normal update can replace Maslow runtime" "$(cat "$log_file")"
pass "normal Maslow update keeps dependency upgrades and ignores runtime packages"

grep -Fq 'pacman -Syu "${runtime_hold_args[@]}" --overwrite' "$ROOT/bin/omarchy-update-system-pkgs" || fail "interactive conflict retry omits the runtime hold"
grep -Fq 'pacman -Syyuu --noconfirm "${runtime_hold_args[@]}"' "$ROOT/bin/omarchy-refresh-pacman" || fail "pacman refresh omits the runtime hold"
grep -Fq 'omarchy-update-runtime-guard filter-packages "${packages[@]}"' "$ROOT/bin/omarchy-reinstall-pkgs" || fail "default reinstall can explicitly override the runtime hold"
grep -Fq 'pacman -Syu --noconfirm --needed "${runtime_hold_args[@]}" "${packages[@]}"' "$ROOT/bin/omarchy-reinstall-pkgs" || fail "default reinstall rediscovers held runtime upgrades"
pass "conflict retry, pacman refresh, and reinstall paths retain the hold"

filtered=$(run_maslow omarchy-update-runtime-guard filter-packages linux omarchy bitwarden omarchy-settings-dev)
[[ $filtered == $'linux\nbitwarden' ]] || fail "explicit reinstall retains held runtime packages" "$filtered"
pass "explicit package lists cannot override the Maslow runtime hold"

for command in omarchy-channel-set omarchy-dev-link; do
  : >"$log_file"
  if run_maslow "$command" stable >"$test_tmp/out" 2>"$test_tmp/err"; then
    fail "$command changes the held Maslow runtime"
  fi
  [[ ! -s $log_file ]] || fail "$command mutates packages before the hold" "$(cat "$log_file")"
done
pass "Maslow channel and dev-link changes stop before mutation"

MASLOW_PRODUCT_FILE="$test_tmp/missing.json" OMARCHY_PATH="$test_tmp/upstream" "$ROOT/bin/omarchy-update-runtime-guard"
[[ -z $(MASLOW_PRODUCT_FILE="$test_tmp/missing.json" OMARCHY_PATH="$test_tmp/upstream" "$ROOT/bin/omarchy-update-runtime-guard" pacman-args) ]] || fail "upstream receives Maslow package ignores"
pass "unbranded upstream behavior remains unchanged"

printf '%s\n' '{not-json' >"$test_tmp/malformed-product.json"
if MASLOW_PRODUCT_FILE="$test_tmp/malformed-product.json" OMARCHY_PATH="$test_tmp/upstream" "$ROOT/bin/omarchy-update-runtime-guard" >"$test_tmp/out" 2>"$test_tmp/err"; then
  fail "malformed installed product metadata disables the runtime hold"
fi
pass "malformed installed product metadata fails closed"

hook="$ROOT/default/libalpm/hooks/01-maslow-runtime-hold.hook"
while IFS='=' read -r _ operation; do
  operation=${operation# }
  [[ $operation == "Install" || $operation == "Upgrade" || $operation == "Remove" ]] || fail "package hook uses unsupported ALPM operation $operation"
done < <(grep '^Operation = ' "$hook")
for package in omarchy omarchy-settings omarchy-dev omarchy-settings-dev; do
  grep -Fx "Target = $package" "$hook" >/dev/null || fail "package hook misses $package"
done
grep -Fx 'AbortOnFail' "$hook" >/dev/null || fail "package hook does not abort explicit replacement"
pass "package-manager hook uses valid operations covering install, upgrade or downgrade, reinstall, and removal"
