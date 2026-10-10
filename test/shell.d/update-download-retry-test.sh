#!/bin/bash

set -euo pipefail

source "$(dirname "$0")/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

stub_bin="$test_tmp/bin"
mkdir -p "$stub_bin"

cat >"$stub_bin/sudo" <<'STUB'
#!/bin/bash
exec "$@"
STUB

# The first -Syu stalls on a download, like pkgs.omarchy.org did on the Lenovo
# (2026-10-10). Later attempts succeed unless STILL_STALLED is set.
cat >"$stub_bin/pacman" <<'STUB'
#!/bin/bash
attempt=$(($(cat "$PACMAN_ATTEMPTS") + 1))
echo "$attempt" >"$PACMAN_ATTEMPTS"
echo "$*" >>"$PACMAN_ARGS"
if ((attempt == 1)) || [[ -n ${STILL_STALLED:-} ]]; then
  echo "error: failed retrieving file 'lmstudio-bin-0.4.26-1-x86_64.pkg.tar.zst' from pkgs.omarchy.org : Operation too slow. Less than 1 bytes/sec transferred the last 10 seconds" >&2
  echo "error: failed to commit transaction (failed to retrieve some files)" >&2
  exit 1
fi
echo "upgrade complete"
STUB

cat >"$stub_bin/omarchy-update-system-pkgs-when-conflicted" <<'STUB'
#!/bin/bash
echo "conflict handler ran" >>"$PACMAN_ARGS"
exit 1
STUB

chmod +x "$stub_bin/sudo" "$stub_bin/pacman" "$stub_bin/omarchy-update-system-pkgs-when-conflicted"

product="$test_tmp/product.json"
echo '{"product":{"id":"maslow-os"}}' >"$product"

run_update() {
  echo 0 >"$test_tmp/attempts"
  : >"$test_tmp/args"
  STILL_STALLED="${STILL_STALLED:-}" \
    PACMAN_ATTEMPTS="$test_tmp/attempts" \
    PACMAN_ARGS="$test_tmp/args" \
    MASLOW_PRODUCT_FILE="$product" \
    PATH="$stub_bin:$ROOT/bin:$PATH" \
    bash "$ROOT/bin/omarchy-update-system-pkgs"
}

output=$(run_update 2>&1) || fail "a stalled download is retried and the update completes" "$output"
[[ $(cat "$test_tmp/attempts") == 2 ]] || fail "exactly one retry after a stalled download"
retry_args=$(sed -n 2p "$test_tmp/args")
[[ $retry_args == *"--disable-download-timeout"* ]] || fail "the retry turns off the stall cutoff" "$retry_args"
[[ $retry_args == *"--ignore omarchy,omarchy-settings,omarchy-dev,omarchy-settings-dev"* ]] || fail "the retry keeps the Maslow runtime held" "$retry_args"
[[ $output == *"download stalled"* ]] || fail "the person is told why the update retries" "$output"
pass "a stalled package download is retried once without the cutoff, keeping the runtime hold"

if output=$(STILL_STALLED=1 run_update 2>&1); then
  fail "a mirror that stays stalled fails the update" "$output"
fi
[[ $(cat "$test_tmp/attempts") == 2 ]] || fail "a stalled mirror is not retried in a loop"
[[ $output == *"try the update again later"* ]] || fail "a stalled mirror explains what to do" "$output"
! grep -q "conflict handler ran" "$test_tmp/args" || fail "a download failure is not treated as a file conflict"
pass "a mirror that stays stalled ends with a clear message and no conflict cleanup"
