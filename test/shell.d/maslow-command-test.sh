#!/bin/bash

set -euo pipefail

source "$(dirname "$0")/base-test.sh"

maslow() { OMARCHY_PATH="$ROOT" "$ROOT/bin/maslow" "$@"; }
omarchy() { OMARCHY_PATH="$ROOT" "$ROOT/bin/omarchy" "$@"; }

help=$(maslow 2>&1)
[[ $help == *"maslow update"* && $help == *"maslow <command> [args...]"* ]] || fail "maslow help shows the product command name" "$help"
[[ $help != *"  omarchy "* ]] || fail "maslow help does not show omarchy as the command" "$help"
pass "maslow help presents the maslow command name"

update_help=$(maslow update --help 2>&1)
[[ $update_help == *"maslow update"* ]] || fail "command help uses the maslow name" "$update_help"
pass "maslow <command> --help uses the maslow name"

[[ $(maslow commands --json) == "$(omarchy commands --json)" ]] || fail "machine-readable output is unchanged for tools"
pass "maslow commands --json is identical to omarchy commands --json"

[[ $(maslow version 2>&1) == "$(omarchy version 2>&1)" ]] || fail "maslow runs the same command as omarchy"
pass "maslow routes every command exactly like omarchy"

set +e
maslow no-such-command-xyz >/dev/null 2>&1
maslow_status=$?
omarchy no-such-command-xyz >/dev/null 2>&1
omarchy_status=$?
set -e
[[ $maslow_status == "$omarchy_status" && $maslow_status != 0 ]] || fail "maslow keeps the router's exit status" "maslow=$maslow_status omarchy=$omarchy_status"
pass "maslow keeps the router's exit status"

listing=$(maslow commands --all 2>&1)
[[ $listing != *"maslow-update"* ]] || fail "binary names such as omarchy-update are not rewritten" "$listing"
pass "binary and path names in help stay intact"
