#!/bin/bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/base-test.sh"

require_command python3
require_command node
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/voice" python3 -m unittest discover -s "$ROOT/voice/tests" -p 'test_*.py'
node "$ROOT/voice/tests/ui-contract-test.mjs"
pass "Voice lifecycle, task boundary, offline workspace and UI contracts"
