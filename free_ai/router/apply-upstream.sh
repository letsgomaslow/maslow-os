#!/bin/bash
set -euo pipefail
router_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
upstream_dir=${1:?Usage: apply-upstream.sh /path/to/dedicated/upstream-checkout}
expected_revision=65ec96df6450224a95a0eabfff8b41b394b2396f
expected_lock=3e6265bd3a3346ca362fd54405e5ed404df72e6a0002cd07d2390dce54463038
[[ $(git -C "$upstream_dir" rev-parse HEAD) == "$expected_revision" ]] || { echo 'Unexpected upstream revision' >&2; exit 1; }
read -r lock_hash _ < <(sha256sum "$upstream_dir/package-lock.json")
[[ $lock_hash == "$expected_lock" ]] || { echo 'Unexpected upstream dependency lock' >&2; exit 1; }
[[ -z $(git -C "$upstream_dir" status --porcelain) ]] || { echo 'Dedicated upstream checkout must be clean' >&2; exit 1; }
git -C "$upstream_dir" apply --check "$router_dir/upstream.patch"
git -C "$upstream_dir" apply "$router_dir/upstream.patch"
mkdir -p "$upstream_dir/server/src/maslow" "$upstream_dir/server/src/__tests__/maslow"
cp "$router_dir/src/maslow-main.ts" "$upstream_dir/server/src/maslow-main.ts"
cp "$router_dir/src/maslow/"*.ts "$upstream_dir/server/src/maslow/"
cp "$router_dir/../tests/router-boundary.test.ts" "$upstream_dir/server/src/__tests__/maslow/boundary.test.ts"
