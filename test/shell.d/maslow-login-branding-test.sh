#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

stub_bin="$test_tmp/bin"
source_logo="$test_tmp/source-logo.png"
packaged_logo="$test_tmp/packaged-logo.png"
installed_logo="$test_tmp/installed-logo.png"
setter_log="$test_tmp/setter.log"
hook_install_log="$test_tmp/hook-install.log"
mkdir -p "$stub_bin"

cat >"$stub_bin/omarchy-plymouth-set-by-theme" <<'STUB'
#!/bin/bash
printf '%s\n' "$*" >>"$MASLOW_TEST_SETTER_LOG"
STUB
cat >"$stub_bin/omarchy-hook-install" <<'STUB'
#!/bin/bash
printf '%s\n' "$*" >>"$MASLOW_TEST_HOOK_INSTALL_LOG"
STUB
cat >"$stub_bin/omarchy-accessibility-sync" <<'STUB'
#!/bin/bash
exit 0
STUB
chmod +x "$stub_bin/omarchy-plymouth-set-by-theme" "$stub_bin/omarchy-hook-install" "$stub_bin/omarchy-accessibility-sync"

run_hook() {
  PATH="$stub_bin:$PATH" \
    OMARCHY_PATH="$ROOT" \
    MASLOW_SOURCE_SDDM_LOGO="$source_logo" \
    MASLOW_PACKAGED_SDDM_LOGO="$packaged_logo" \
    MASLOW_INSTALLED_SDDM_LOGO="$installed_logo" \
    MASLOW_TEST_SETTER_LOG="$setter_log" \
    bash "$ROOT/install/user/first-run/maslow-login-branding.hook"
}

printf '%s\n' 'MASLOW' >"$source_logo"
printf '%s\n' 'UPSTREAM' >"$packaged_logo"
cp "$source_logo" "$installed_logo"
run_hook
[[ ! -e $setter_log ]] || fail "matching Maslow login artwork is not republished"
pass "matching Maslow login artwork needs no repair"

cp "$packaged_logo" "$installed_logo"
run_hook
grep -Fxq 'maslow-dark' "$setter_log" || fail "an upstream package reset restores the Maslow login theme"
pass "an upstream package reset restores the Maslow login theme"

rm -f "$setter_log"
printf '%s\n' 'OWNER CUSTOM THEME' >"$installed_logo"
run_hook
[[ ! -e $setter_log ]] || fail "owner-selected login artwork is preserved"
pass "owner-selected login artwork is preserved"

rm -f "$installed_logo"
run_hook
[[ ! -e $setter_log ]] || fail "missing login assets are ignored safely"
pass "missing login assets are ignored safely"

PATH="$stub_bin:$PATH" \
  OMARCHY_PATH="$ROOT" \
  MASLOW_TEST_HOOK_INSTALL_LOG="$hook_install_log" \
  bash "$ROOT/migrations/1788337736.sh"
grep -Fxq "post-update $ROOT/install/user/first-run/maslow-login-branding.hook" "$hook_install_log" ||
  fail "the migration installs the update-safe login branding hook"
pass "the migration installs the update-safe login branding hook"
