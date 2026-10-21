#!/bin/bash

# Renders the real ScreensaverScene offscreen with the software renderer, the
# path the gallery uses, so it needs no compositor and never draws on the
# session running the test. The Service refusal paths need a Wayland
# compositor for PanelWindow and run only when one answers; none of them maps
# an overlay.
#
# Gallery: GALLERY_OUTPUT=<dir> [SCREENS=1440x900,1280x800,1920x1080]
# [GALLERY_TIMES=0,2800,6300,24250] [REDUCED=1] with the same environment as
# run_fixture below saves one PNG per size and time.

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

TMPDIR=""
QS_PID=""

cleanup() {
  if [[ -n $QS_PID ]] && kill -0 "$QS_PID" 2>/dev/null; then
    kill "$QS_PID" 2>/dev/null || true
    wait "$QS_PID" 2>/dev/null || true
  fi
  if [[ -n $TMPDIR && -d $TMPDIR ]]; then
    rm -rf "$TMPDIR"
  fi
}
trap cleanup EXIT

if ! command -v quickshell >/dev/null 2>&1; then
  pass "quickshell not installed; skipping screensaver render test"
  exit 0
fi

require_command jq

TMPDIR=$(mktemp -d)

# run_fixture <name> <fixture.qml> <platform> waits for the fixture's result.
run_fixture() {
  local name=$1 fixture=$2 platform=$3
  local config_dir="$TMPDIR/$name"
  local result="$TMPDIR/$name.json"
  local log="$TMPDIR/$name.log"
  local home="$TMPDIR/$name-home"
  local runtime="$TMPDIR/$name-run"

  mkdir -p "$config_dir" "$home/.local/state/omarchy/toggles/hypr" "$runtime"
  chmod 700 "$runtime"
  cp "$SHELL_TEST_DIR/fixtures/screensaver-preview/$fixture" "$config_dir/shell.qml"
  ln -s "$ROOT/shell/Ui" "$config_dir/Ui"
  ln -s "$ROOT/shell/Commons" "$config_dir/Commons"
  ln -s "$ROOT/shell/plugins/screensaver" "$config_dir/screensaver"
  printf '%s\n' '-- reduced motion' >"$home/.local/state/omarchy/toggles/hypr/reduced-motion.lua"

  local -a env_args=(
    OMARCHY_PATH="$ROOT"
    OMARCHY_QML_TEST_RESULT="$result"
    HOME="$home"
    XDG_CONFIG_HOME="$home/.config"
    XDG_CACHE_HOME="$home/.cache"
    XDG_STATE_HOME="$home/.local/state"
    QML2_IMPORT_PATH="$ROOT/shell${QML2_IMPORT_PATH:+:$QML2_IMPORT_PATH}"
    QML_IMPORT_PATH="$ROOT/shell${QML_IMPORT_PATH:+:$QML_IMPORT_PATH}"
    PATH="$ROOT/bin:$PATH"
  )
  if [[ $platform == "offscreen" ]]; then
    env_args+=(
      XDG_RUNTIME_DIR="$runtime"
      QT_QPA_PLATFORM=offscreen
      QT_QPA_PLATFORMTHEME=generic
      QT_QUICK_BACKEND=software
    )
    env -u WAYLAND_DISPLAY -u HYPRLAND_INSTANCE_SIGNATURE -u DISPLAY -u GALLERY_OUTPUT -u REDUCED "${env_args[@]}" \
      quickshell -p "$config_dir" --no-color >"$log" 2>&1 &
  else
    env -u GALLERY_OUTPUT -u REDUCED "${env_args[@]}" quickshell -p "$config_dir" --no-color >"$log" 2>&1 &
  fi
  QS_PID=$!

  for _ in {1..150}; do
    [[ -s $result ]] && break
    if ! kill -0 "$QS_PID" 2>/dev/null; then
      sed -n '1,220p' "$log" >&2
      fail "screensaver $name quickshell exited before writing result"
    fi
    sleep 0.1
  done

  [[ -s $result ]] || {
    sed -n '1,220p' "$log" >&2
    fail "screensaver $name test timed out"
  }

  kill "$QS_PID" 2>/dev/null || true
  wait "$QS_PID" 2>/dev/null || true
  QS_PID=""

  if ! jq -e '.ok == true' "$result" >/dev/null; then
    printf 'Screensaver %s result:\n' "$name" >&2
    jq . "$result" >&2
    printf 'Screensaver %s log:\n' "$name" >&2
    sed -n '1,220p' "$log" >&2
    return 1
  fi
}

scene_check="screensaver scene loads every image and keeps the mark, wordmark, clock and hint on one axis on screen at 1440x900, 1280x800 and 1920x1080, with a still Reduced Motion frame"
run_fixture scene shell.qml offscreen || fail "$scene_check"
pass "$scene_check"

if compositor_reachable; then
  ulimit -c 0 2>/dev/null || true
  service_check="screensaver service resolves motion and refuses classic, locked and inert shows without mapping"
  run_fixture service service.qml wayland || fail "$service_check"
  pass "$service_check"
else
  pass "no Wayland compositor; skipping screensaver service refusal checks"
fi
