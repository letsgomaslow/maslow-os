#!/usr/bin/env bash

set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
RESET="$ROOT/bin/omarchy-system-factory-reset"

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'ok - %s\n' "$1"
}

eval "$(sed -n '/^resolve_fstab_device() {/,/^}/p' "$RESET")"

[[ $(resolve_fstab_device UUID=BBD4-BCB6) == /dev/disk/by-uuid/BBD4-BCB6 ]] ||
  fail 'UUID ESP sources resolve through by-uuid'
[[ $(resolve_fstab_device LABEL=OMBOOT) == /dev/disk/by-label/OMBOOT ]] ||
  fail 'label ESP sources resolve through by-label'
[[ $(resolve_fstab_device PARTUUID=1234-5678) == /dev/disk/by-partuuid/1234-5678 ]] ||
  fail 'partition UUID ESP sources resolve through by-partuuid'
[[ $(resolve_fstab_device PARTLABEL=ESP) == /dev/disk/by-partlabel/ESP ]] ||
  fail 'partition label ESP sources resolve through by-partlabel'
[[ $(resolve_fstab_device /dev/vda1) == /dev/vda1 ]] ||
  fail 'absolute ESP device paths pass through unchanged'
if resolve_fstab_device tmpfs >/dev/null 2>&1; then
  fail 'unsupported ESP source syntax must be rejected'
fi

pass 'factory reset resolves every supported fstab device syntax'
