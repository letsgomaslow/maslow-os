#!/bin/bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/base-test.sh"

require_command python3
require_command node

# The test suite imports the SDKs pinned in voice/requirements.lock. An
# installed Maslow Voice package provides that exact environment; source-only
# development can pass MASLOW_VOICE_PYTHON to use its prepared pinned venv.
voice_python=${MASLOW_VOICE_PYTHON:-}
if [[ -z $voice_python && -x /usr/lib/maslow-voice/venv/bin/python ]]; then
  voice_python=/usr/lib/maslow-voice/venv/bin/python
fi
[[ -n $voice_python && -x $voice_python ]] ||
  fail "Voice tests require the pinned Python environment; set MASLOW_VOICE_PYTHON to its python executable"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/voice" "$voice_python" -m unittest discover -s "$ROOT/voice/tests" -p 'test_*.py'
node "$ROOT/voice/tests/ui-contract-test.mjs"
node "$ROOT/voice/tests/orb-contract-test.mjs"
pass "Voice lifecycle, task boundary, offline workspace and UI contracts"
