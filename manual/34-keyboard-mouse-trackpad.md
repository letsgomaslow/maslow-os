# Keyboard, Mouse, Trackpad

Hyprland lets you configure all your inputs in great detail. You can change the keyboard repeat to be supersonically fast or make the trackpad use natural scrolling. You change all of it in `~/.config/hypr/input.lua`, which you can also reach via _Setup > Input_ in the Maslow OS menu (`Super + Space`). Anything you set there replaces Omarchy's defaults.

Here's an example:

```lua
hl.config({
  input = {
    -- Use multiple keyboard layouts and switch between them with Left Alt + Right Alt
    kb_layout = "us,dk",
    kb_options = "compose:caps,shift:both_capslock_cancel,grp:alts_toggle",

    -- Change speed of keyboard repeat
    repeat_rate = 40,
    repeat_delay = 600,

    -- Increase sensitivity for mouse/trackpad (default: 0)
    sensitivity = 0.35,

    touchpad = {
      -- Use natural (inverse) scrolling
      natural_scroll = true,

      -- Use two-finger clicks for right-click instead of lower-right corner
      clickfinger_behavior = true,

      -- Control the speed of your scrolling
      scroll_factor = 0.3,
    },
  },
})

-- Scroll faster in the terminal
o.window("(Alacritty|kitty|foot)", { scroll_touchpad = 1.5 })
```

You can [see all the input options](https://wiki.hypr.land/Configuring/Basics/Variables/#input) on the Hyprland wiki for inputs.

By default, Maslow OS uses Caps Lock as the compose key for [quick emojis](07-hotkeys.md#quick-emojis) and [other completions](07-hotkeys.md#quick-completions). To use Caps Lock normally, move the compose key elsewhere by changing `compose:caps` in `kb_options`. For example, this moves the compose key to Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Trackpad gestures

You can also turn on [touchpad gestures](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), like swiping with three fingers to change workspaces:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

On Dell XPS laptops with a haptic touchpad, you can also set the click strength to low, mid, or high under _Trigger > Hardware > Touchpad Haptics_.

### Typing in Chinese, Japanese, and other languages

Maslow OS runs the [fcitx5](https://fcitx-im.org/) input method framework in every session; it powers the Caps Lock compose sequences. The foundation for non-Latin input is therefore already present. Install an input engine such as `fcitx5-mozc` for Japanese or `fcitx5-chinese-addons` for Chinese with `omarchy pkg add`, plus `fcitx5-configtool` to add the engine and configure its switching key.

### Use ALT as SUPER

On some keyboards, it's not convenient to use the primary meta key (Windows/cmd key) as SUPER. You can change this to be ALT instead using this change:

```lua
hl.config({
  input = {
    kb_options = "compose:caps,shift:both_capslock_cancel,altwin:swap_alt_win",
  },
})
```
