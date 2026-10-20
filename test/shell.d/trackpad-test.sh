#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

require_command lua
require_command jq

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

stub_dir="$tmpdir/bin"
home_dir="$tmpdir/home"
log_file="$tmpdir/hyprctl.log"
mkdir -p "$stub_dir" "$home_dir"

settings_file="$home_dir/.local/state/omarchy/toggles/hypr/trackpad-settings"

# getoption answers from LIVE_<option> variables so a test can model whatever
# the user's own config left in place.
cat >"$stub_dir/hyprctl" <<'EOF'
#!/bin/bash
case $1 in
  getoption)
    var="LIVE_${2##*:}"
    printf '{"option": "%s", "bool": %s, "set": true }\n' "$2" "${!var:-false}"
    ;;
  reload) printf 'reload\n' >>"$HYPRCTL_LOG" ;;
esac
EOF
chmod +x "$stub_dir/hyprctl"

cat >"$stub_dir/omarchy-hw-touchpad" <<'EOF'
#!/bin/bash
[[ -n ${TOUCHPAD_NAME:-} ]] && printf '%s\n' "$TOUCHPAD_NAME"
EOF
chmod +x "$stub_dir/omarchy-hw-touchpad"

run_cmd() {
  HOME="$home_dir" HYPRCTL_LOG="$log_file" TOUCHPAD_NAME="${TOUCHPAD_NAME-bcm5974}" \
    PATH="$stub_dir:$ROOT/bin:$PATH" "$ROOT/bin/$@"
}

value_of() {
  sed -n "s/^$1=//p" "$settings_file"
}

: >"$log_file"
run_cmd omarchy-trackpad-set natural-scroll on
[[ $(value_of natural_scroll) == "true" ]] || fail "set on stores natural_scroll=true"
grep -qx reload "$log_file" || fail "set reloads Hyprland"
pass "set on stores the choice and reloads"

run_cmd omarchy-trackpad-set natural-scroll off
[[ $(value_of natural_scroll) == "false" ]] || fail "set off stores natural_scroll=false"
(( $(grep -c '^natural_scroll=' "$settings_file") == 1 )) || fail "set replaces an earlier value instead of appending"
pass "set off replaces the earlier value"

LIVE_tap_to_click=true run_cmd omarchy-trackpad-set tap-to-click
[[ $(value_of tap_to_click) == "false" ]] || fail "toggle turns off a setting that is live on"
LIVE_tap_to_click=false run_cmd omarchy-trackpad-set tap-to-click toggle
[[ $(value_of tap_to_click) == "true" ]] || fail "toggle turns on a setting that is live off"
pass "toggle flips the live Hyprland value, including user config"

run_cmd omarchy-trackpad-set workspace-swipe toggle
[[ $(value_of workspace_swipe) == "true" ]] || fail "swipe toggle turns the gesture on"
run_cmd omarchy-trackpad-set workspace-swipe toggle
[[ $(value_of workspace_swipe) == "false" ]] || fail "swipe toggle turns the gesture off"
pass "workspace swipe toggles from its stored value"

run_cmd omarchy-trackpad-set three-finger-drag on
[[ $(value_of drag_3fg) == "true" ]] || fail "three-finger drag stores drag_3fg=true"
pass "three-finger drag is a stored setting"

run_cmd omarchy-trackpad-set window-gestures toggle
[[ $(value_of window_gestures) == "true" ]] || fail "window gestures toggle on from their stored value"
pass "window gestures are a stored setting"

run_cmd omarchy-trackpad-set speed 0.35
[[ $(value_of sensitivity) == "0.35" && $(value_of device) == "bcm5974" ]] ||
  fail "speed stores the value and the device it applies to"
for bad in 2 -1.5 abc '0.3; rm -rf /' ''; do
  if run_cmd omarchy-trackpad-set speed "$bad" 2>/dev/null; then
    fail "speed rejects '$bad'"
  fi
done
[[ $(value_of sensitivity) == "0.35" ]] || fail "a rejected speed leaves the stored value alone"
pass "speed accepts -1..1 and rejects anything else"

if TOUCHPAD_NAME= run_cmd omarchy-trackpad-set speed 0.2 2>/dev/null; then
  fail "speed fails without a touchpad"
fi
pass "speed needs a detected touchpad"

if run_cmd omarchy-trackpad-set bogus on 2>/dev/null; then
  fail "unknown settings are rejected"
fi
if run_cmd omarchy-trackpad-set natural-scroll maybe 2>/dev/null; then
  fail "unknown actions are rejected"
fi
pass "unknown settings and actions are rejected"

status=$(LIVE_tap_to_click=false LIVE_natural_scroll=true LIVE_clickfinger_behavior=true LIVE_disable_while_typing=true LIVE_drag_3fg=true \
  run_cmd omarchy-trackpad-status)
[[ $status == *$'present\ttrue'* && $status == *$'device\tbcm5974'* && $status == *$'enabled\ttrue'* ]] ||
  fail "status reports the device" "$status"
[[ $status == *$'tap_to_click\tfalse'* && $status == *$'natural_scroll\ttrue'* && $status == *$'workspace_swipe\tfalse'* && $status == *$'drag_3fg\ttrue'* && $status == *$'speed\t0.35'* ]] ||
  fail "status reports live options and stored choices" "$status"
pass "status reports live options and stored choices"

[[ $(TOUCHPAD_NAME= run_cmd omarchy-trackpad-status) == $'present\tfalse' ]] ||
  fail "status reports no trackpad when none is detected"
pass "status reports a missing trackpad"

run_cmd omarchy-trackpad-set reset
[[ ! -e $settings_file ]] || fail "reset removes stored choices"
pass "reset removes stored choices"

# The Lua loader must apply only whitelisted, validated values and treat the
# device name as data.
apply_settings() {
  mkdir -p "$(dirname "$settings_file")"
  printf '%s' "$1" >"$settings_file"
  HOME="$home_dir" OMARCHY_PATH="$ROOT" lua - <<'LUA'
package.path = os.getenv("OMARCHY_PATH") .. "/?.lua;" .. package.path
local out = {}
hl = {
  config = function(c)
    local keys = {}
    for k, v in pairs(c.input.touchpad) do table.insert(keys, k .. "=" .. tostring(v)) end
    table.sort(keys)
    table.insert(out, "config " .. table.concat(keys, ","))
  end,
  gesture = function(g) table.insert(out, "gesture " .. g.fingers .. " " .. g.direction .. " " .. g.action .. (g.mods and (" " .. g.mods) or "")) end,
  device = function(d) table.insert(out, "device " .. d.name .. " " .. tostring(d.sensitivity)) end,
}
require("default.hypr.trackpad-settings")
print(table.concat(out, "\n"))
LUA
}

actual=$(apply_settings $'tap_to_click=false\nnatural_scroll=true\nworkspace_swipe=true\ndevice=bcm5974\nsensitivity=0.35\n')
expected=$'config natural_scroll=true,tap_to_click=false\ngesture 3 horizontal workspace\ndevice bcm5974 0.35'
[[ $actual == "$expected" ]] || fail "loader applies stored choices" "expected: $expected"$'\n'"actual:   $actual"
pass "loader applies stored choices"

actual=$(apply_settings $'drag_3fg=true\nworkspace_swipe=true\n')
expected=$'config drag_3fg=1\ngesture 4 horizontal workspace'
[[ $actual == "$expected" ]] || fail "three-finger drag moves the workspace swipe to four fingers" "expected: $expected"$'\n'"actual:   $actual"
pass "three-finger drag moves the workspace swipe to four fingers"

actual=$(apply_settings $'drag_3fg=true\nwindow_gestures=true\nworkspace_swipe=true\n')
expected=$'config drag_3fg=1\ngesture 4 swipe resize SUPER\ngesture 4 horizontal workspace'
[[ $actual == "$expected" ]] || fail "window gestures resize on Super + four fingers before the workspace swipe" "expected: $expected"$'\n'"actual:   $actual"
pass "window gestures resize on Super + four fingers before the workspace swipe"

actual=$(apply_settings $'window_gestures=true\n')
expected=$'gesture 3 swipe move SUPER\ngesture 4 swipe resize SUPER'
[[ $actual == "$expected" ]] || fail "without drag, window gestures move on Super + three fingers" "expected: $expected"$'\n'"actual:   $actual"
pass "without drag, window gestures move on Super + three fingers"

actual=$(apply_settings $'drag_3fg=false\n')
[[ $actual == "config drag_3fg=0" ]] || fail "three-finger drag off sets drag_3fg=0" "$actual"
pass "three-finger drag off sets drag_3fg=0"

actual=$(apply_settings $'natural_scroll=yes\nos.execute=true\nsensitivity=5\ndevice=bcm5974\nworkspace_swipe=1\n')
[[ -z $actual ]] || fail "loader ignores invalid values and unknown keys" "$actual"
pass "loader ignores invalid values and unknown keys"

actual=$(apply_settings $'device=x"); os.exit(1) --\nsensitivity=0.1\n')
[[ $actual == 'device x"); os.exit(1) -- 0.1' ]] || fail "loader passes the device name as data" "$actual"
pass "loader passes the device name as data"

run_node_test <<'JS'
const trackpad = requireFromRoot('shell/plugins/panels/trackpad/Model.js')

const status = trackpad.parseStatus('present\ttrue\ndevice\tbcm5974\nenabled\ttrue\ntap_to_click\ttrue\nnatural_scroll\tfalse\nclickfinger_behavior\ttrue\ndisable_while_typing\ttrue\nworkspace_swipe\tfalse\nspeed\t0.35\n')
assertEqual(status.present, true, 'trackpad parses presence')
assertEqual(status.device, 'bcm5974', 'trackpad parses the device name')
assertEqual(status.natural_scroll, false, 'trackpad parses booleans')
assertEqual(status.speed, 0.35, 'trackpad parses speed')
assertEqual(trackpad.parseStatus('speed\t9').speed, 1, 'trackpad clamps speed')
assertEqual(trackpad.parseStatus('').present, false, 'trackpad treats empty output as absent')

const rows = trackpad.settingRows(status)
assertDeepEqual(rows.map(r => r.command), ['tap-to-click', 'two-finger-right-click', 'natural-scroll', 'three-finger-drag', 'workspace-swipe', 'window-gestures', 'ignore-while-typing'], 'trackpad lists every setting command')

const dragging = Object.assign({}, status, { drag_3fg: true, workspace_swipe: true })
const dragRows = trackpad.settingRows(dragging)
assertEqual(dragRows[4].label, 'Four-finger workspace swipe', 'swipe setting names four fingers while dragging with three')
const dragGuide = trackpad.guideRows(dragging).map(r => r.fingers + ' ' + r.gesture + ' ' + r.action)
assert(dragGuide.includes('3 Rest and slide Drag'), 'guide shows three-finger drag')
assert(dragGuide.includes('4 Swipe left or right Switch workspace'), 'guide moves the swipe to four fingers while dragging')

const windowGuide = trackpad.guideRows(Object.assign({}, dragging, { window_gestures: true })).map(r => r.fingers + ' ' + r.gesture + ' ' + r.action)
assert(windowGuide.includes('3 Hold Super, drag Move window'), 'guide shows Super + three-finger drag moves windows')
assert(windowGuide.includes('4 Hold Super, swipe Resize window'), 'guide shows Super + four-finger swipe resizes windows')
const swipeMove = trackpad.guideRows(Object.assign({}, status, { window_gestures: true })).map(r => r.fingers + ' ' + r.gesture + ' ' + r.action)
assert(swipeMove.includes('3 Hold Super, swipe Move window'), 'guide shows Super + three-finger swipe moves windows without drag')
assertEqual(rows[0].checked, true, 'trackpad reflects tap-to-click state')

const twoFinger = trackpad.guideRows(status).map(r => r.fingers + ' ' + r.gesture + ' ' + r.action)
assert(twoFinger.includes('2 Press down Right click'), 'guide shows two-finger right click')
assert(twoFinger.includes('2 Tap Right click'), 'guide shows tap right click when tapping is on')
assert(!twoFinger.some(r => r.includes('workspace')), 'guide hides swipe while it is off')

const corner = trackpad.guideRows(Object.assign({}, status, { clickfinger_behavior: false, tap_to_click: false, workspace_swipe: true }))
  .map(r => r.fingers + ' ' + r.gesture + ' ' + r.action)
assert(corner.includes('1 Press bottom-right corner Right click'), 'guide shows corner right click')
assert(!corner.some(r => r.includes(' Tap ')), 'guide hides taps while tapping is off')
assert(corner.includes('3 Swipe left or right Switch workspace'), 'guide shows swipe when on')

assertEqual(trackpad.speedLabel(0), 'Default', 'speed label names the default')
assertEqual(trackpad.speedLabel(0.35), '+35%', 'speed label shows positive speed')
assertEqual(trackpad.speedLabel(-0.5), '-50%', 'speed label shows negative speed')
JS
