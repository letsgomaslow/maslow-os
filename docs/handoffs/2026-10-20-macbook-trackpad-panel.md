# MacBook trackpad diagnosis and Trackpad panel — October 20, 2026

## Current state and evidence boundary

The user reported on the 2012 15-inch Retina MacBook Pro (MacBookPro10,1) that the trackpad "kind of works" but right click and click are unreliable, and asked for a widget that explains the trackpad and switches features on and off. This session diagnosed the input stack directly, enabled the three-finger workspace swipe on the user's machine (user-confirmed working), fixed a touchpad-detection defect, and built a Trackpad bar panel on branch `feature/trackpad-panel`. The panel is source-tested and visually checked in the real running shell as a temporary user plugin; it is not packaged, installed or dev-linked, so its switches do not change live Hyprland behavior on the installed system yet.

## Directly observed facts

- The trackpad is USB `05ac:0262`, driven by `bcm5974` as a buttonpad (`INPUT_PROP_POINTER | INPUT_PROP_BUTTONPAD`, a single `BTN_LEFT`). libinput 1.32.0 ships a matching quirk for this exact device in `50-system-apple.quirks`. Kernel warnings in the boot log come from the Broadcom `wl` Wi-Fi module, not the trackpad.
- Live Hyprland options before this work: `clickfinger_behavior=true`, `tap_to_click=true` (default), `natural_scroll=false`, `disable_while_typing=true`. Right click is therefore software-produced by two-finger press or tap.
- Three-finger workspace swipe ships commented out in `config/hypr/input.lua`. The user's `~/.config/hypr/input.lua` line was uncommented (backup alongside); `hyprctl reload` and `hyprctl configerrors` were clean and the user confirmed the swipe works.
- Correction: `omarchy-hw-touchpad` on `main` only matched names containing `touchpad` or `trackpad`, so it returns nothing for `bcm5974`. The **installed** candidate (`omarchy-dev 4.0.0.r3146.g1056a75`, not an ancestor of `main`) already carries upstream's udev `ID_INPUT_TOUCHPAD` fallback and returns `bcm5974`, so the menu Touchpad toggle works on this machine. An earlier statement that it was hidden on the MacBook was wrong. The branch's name-match fix only affects `main`; upstream's udev fallback is the better long-term fix when `main` converges. A brief disable/re-enable check confirmed a disabled `bcm5974` stays listed in `hyprctl devices`.
- Click diagnosis, from two user-run captures (`libinput debug-events --verbose`, 60 s, and `libinput record` raw evdev, 20 s; logs stayed in the session scratchpad and are not committed). Taps are reliable: every one-, two- and three-finger tap produced left, right and middle click respectively, and three-finger swipes and two-finger scroll worked. The physical click is unreliable at the hardware level: the raw capture shows the kernel receiving `BTN_LEFT` for only 2 of 8 touches; a firm one-finger press held 1.7 s clicked, while a one-finger 0.7 s touch did not. libinput handles every click that arrives correctly, so no software setting makes the switch more reliable. Five touches reported three contacts landing at once; whether the user used one finger is unconfirmed. The likely cause, consistent with but **not proven by** this evidence, is a swollen battery under the trackpad (49.5% design capacity after 1187 cycles, recorded October 18). The user was advised to check for swelling and to rely on taps.
- Mitigation applied on the user's machine (user-requested): three-finger drag (`drag_3fg = 1`) and the workspace swipe moved to four fingers in `~/.config/hypr/input.lua` (backups alongside). Reload and `configerrors` clean; live `input:touchpad:drag_3fg` reads 1. The user has not yet reported back on how the drag feels.

## Source changes on `feature/trackpad-panel`

- `bin/omarchy-hw-touchpad`: also matches `bcm5974` (relevant to `main` only; see correction above).
- `bin/omarchy-trackpad-set` / `bin/omarchy-trackpad-status` and `GROUP_DESCRIPTIONS[trackpad]`: store tap-to-click, two-finger right click, natural scrolling, three-finger workspace swipe, ignore-while-typing and pointer speed as validated `key=value` data in `~/.local/state/omarchy/toggles/hypr/trackpad-settings`; status reports live Hyprland values so user config is reflected truthfully.
- `default/hypr/trackpad-settings.lua`, loaded from `default/hypr/toggles.lua` after user config and before the persisted device disable: applies only whitelisted keys with validated values; the device name is passed as data.
- Three-finger drag is a panel setting (`omarchy trackpad set three-finger-drag`); while it is on, the loader moves the workspace swipe to four fingers, and the switch label and guide say so.
- `shell/plugins/panels/trackpad/` (`omarchy.trackpad` bar widget): hidden without a touchpad; Settings view with switches and a speed slider, How to use view whose gesture list follows the current settings; master on/off reuses `omarchy-toggle-touchpad`. Accessibility: every control has an accessible role/name/state, keyboard cursor covers every control (arrows, Enter, Tab between panels), helper text uses body-small size at 0.85 opacity, gesture text wraps instead of eliding, and the Off state shows keyboard recovery text (Super + Ctrl + H, then Touchpad). On this 1440x900 logical screen the Settings view is taller than the screen, so the content scrolls with a visible indicator in its own gutter, the keyboard cursor scrolls into view, the slider's cursor ring uses the theme hover-cursor border, and rows scrolling under a parked pointer no longer steal the keyboard cursor (hover only counts after real pointer motion).
- Default bar layout adds `omarchy.trackpad` after `omarchy.audio`; migration `1792530174.sh` puts it on existing bars. `test/shell.d/agents-default-migration-test.sh` expectation updated because its fixture is the shipped layout.

## Tests and verification

- `test/shell.d/trackpad-test.sh`: 36 passing checks (commands with stubbed `hyprctl`, Lua loader validation including hostile values, panel model).
- `./test/cli` passes. `./test/shell` fails only in `network-captive-portal`, `snapper` and `unowned-system-paths`, which fail identically on unchanged `main` (missing packages checkout / QML fixture environment).
- Visual: real running shell with the panel installed temporarily as `local.trackpad-preview` (commands routed to the checkout); inspected Settings, How to use, and a simulated Off state (status output rewritten, trackpad not actually disabled). After adding three-finger drag: inspected overflow, scrolling and the slider cursor ring with real keystrokes from `wtype`; a temporary debug log confirmed the cursor stays on the slider. Preview setting commands were stubbed so no settings file was written. The preview was removed and `~/.config/omarchy/shell.json` restored byte-equivalent afterwards. Only the light theme active on this machine was inspected; dark themes are not visually checked.
- Not tested: switches changing live behavior on an installed build, screen-reader (Orca) announcement, packaging, ISO.

## Local test layer on the MacBook (October 20)

`omarchy dev link` is refused by `omarchy-update-runtime-guard` on this build ("dev-link switching is disabled to protect the finalized desktop experience"), and the installed runtime is a candidate that `main` does not contain, so the branch was not dev-linked. Instead, at the user's request, a reversible user-level layer runs the branch's trackpad pieces on top of the installed runtime:

- `~/.local/bin/omarchy-trackpad-set|status` symlink to the checkout.
- `~/.config/hypr/hyprland.lua` ends with a marked block that `dofile`s the checkout's `default/hypr/trackpad-settings.lua` and then re-applies the persisted touchpad disable (Hyprland exposes no readable per-device enabled state, so ordering could not be verified directly).
- `~/.config/omarchy/plugins/local.trackpad` is a copy of the panel with the reserved `omarchy.*` id rewritten; it is on the bar after `omarchy.audio`.
- Drag and the four-finger swipe moved from personal `input.lua` lines into the panel's settings file; `input.lua` is byte-identical to its pre-session backup.
- `~/.config/omarchy/shell.toml` carries the raised highlight values for live testing.
- `~/.local/state/maslow-trackpad-test/sync.sh` re-copies the panel after source edits; `uninstall.sh` removes that `shell.toml` if still the test file, restores the backed-up `hyprland.lua`, `input.lua` and `shell.json`, removes the layer and keeps drag/four-finger swipe as personal lines if drag was on.

Verified: panel renders live with truthful states; `omarchy-trackpad-set natural-scroll on|off` changed live `input:touchpad:natural_scroll` and back with drag intact; `configerrors` empty. User testing is pending.

## Omarchy-native gestures (October 20, later)

The user reported that three-finger drag could not move apps: Omarchy windows have no title bars and move with Super + left-drag (`hl.dsp.window.drag()`) and resize with Super + right-drag. Added, each as a panel switch with guide lines and stored-only state (Hyprland exposes no readable gesture state):

- Window gestures: Super + three-finger drag moves (drag holds the left button into the existing binding; without drag, a Super + three-finger swipe `move` gesture), Super + four-finger swipe `resize`. The user called the result "great"; which specific gestures they exercised was not itemised.
- Six user-selected shortcuts: four-finger swipe up opens `omarchy-menu toggle root`; Alt + four-finger swipe up runs `omarchy-launch-voice start` (opens Voice only, same as Super + H); four-finger swipe down toggles the `scratchpad` special workspace; four-finger pinch out fullscreens; four-finger pinch in floats; Super + four-finger pinch is `cursorZoom` (zoom_level 2). "Close window" was deliberately not put on a gesture.
- Hyprland 0.56.2 accepts `mods` on `hl.gesture` and reports shadowed gestures as errors; with all gestures enabled `configerrors` is empty. Gesture behaviour itself is user-pending (only definitions and registration are verified).
- A QML syntax slip briefly removed the widget from the live bar; it was fixed within minutes and `trackpad-test.sh` now fails on `qmllint` `[syntax]` findings. In the guide view, Up/Down at the view tabs now scroll the overflowing guide for keyboard users.
- Keyboard highlight contrast (user-approved, theme-wide): the `hover-cursor` border drew at 0.25 alpha, fainter than idle 0.4 borders, and Maslow menu rows had a zero-width selected border. Defaults in `Style.qml`, `Color.qml`, `Menu.qml` and `default/themed/shell.toml.tpl` now use 0.9 cursor/focus border alpha with 0.12 fill, and a 1px 0.9-alpha outline on the selected menu row (rows already reserve that width). Measured in the light theme on the MacBook: highlight outline 17.6:1 against the panel background and 13.3:1 against its fill. Verified live in the Trackpad panel, Audio panel and Maslow menu via a temporary `~/.config/omarchy/shell.toml` override (the installed template is unchanged until a package ships); dark themes were not rendered. Not changed: idle row borders measure 2.8:1; the `[launcher]` template section has no first-party consumer and the bundled third-party app launcher stays as shipped. `row-border-stability` and `button-border-stability` tests pass; `./test/shell` fails only in `config`, `network-captive-portal`, `snapper` and `unowned-system-paths`, all failing identically on `main` for the missing packages checkout / QML fixture.

Tests: `trackpad-test.sh` 54 passing; `./test/cli` passes.

## Remaining gates and next action

The user's swipe and three-finger drag currently come from their personal config lines; once this branch is installed, move them to `omarchy trackpad set workspace-swipe on` and `omarchy trackpad set three-finger-drag on` and remove the lines so the panel switches own them. The branch is not pushed; the user chose local testing first, via the layer above. The physical-click fault is hardware-side and needs a battery/trackpad inspection, not code.

Next action: collect the user's findings from testing the local layer, fix confirmed issues in the checkout and re-run `sync.sh`, then decide with the user on pull request and package delivery.
