# Toggles, Idle & the Screensaver

A lot of what you change day to day isn't really a setting. It's a mode you flip on for an hour and off again: night light while you're working late, do not disturb while you're presenting, or stay awake while you're watching something. Maslow OS calls these toggles, and each one uses the same underlying switch whether you choose a hotkey, menu entry, or command.

### The toggle menu

`Super + Ctrl + O` opens _Trigger > Toggle_ directly, or you can walk there from the Maslow OS menu (`Super + Space`). Everything in that list is a switch you can flip without thinking about where the state lives.

From the terminal, the same switches are `omarchy toggle <thing>`. Run `omarchy toggle` on its own to see the whole group.

| Toggle | Hotkey | Command |
| ------ | ------ | ------- |
| Night light | `Super + Ctrl + N` | `omarchy toggle nightlight` |
| Silence notifications | `Super + Ctrl + ,` | `omarchy toggle notification silencing` |
| Stay awake (no idle lock) | `Super + Ctrl + I` | `omarchy toggle idle` |
| Crash capture | — | `omarchy toggle crash-capture` |
| Screensaver | — | `omarchy toggle screensaver` |
| Menu bar | `Super + Shift + Space` | `omarchy toggle bar` |
| Touchpad | `XF86TouchpadToggle` | `omarchy toggle touchpad` |
| Touchscreen | — | `omarchy toggle touchscreen` |
| Suspend | — | `omarchy toggle suspend` |
| Hybrid GPU | — | `omarchy toggle hybrid gpu` |

The touchpad, touchscreen, and hybrid GPU switches live under _Trigger > Hardware_ (`Super + Ctrl + H`) rather than under Toggle, since they only show up when you actually have that hardware. The touchpad and touchscreen ones survive a Hyprland reload — the disabled device's name is saved to a small state file that Hyprland reads on startup to disable it again.

The Toggle menu also carries a few things that aren't `omarchy toggle` commands but behave the same: battery percentage in the bar, workspace layout (`Super + L`), window gaps (`Super + Shift + Backspace`), and the 1-window square aspect (`Super + Ctrl + Backspace`).

Most of these are just a flag file under `~/.local/state/omarchy/toggles/`. If you want to branch on one in a script, `omarchy-toggle-enabled` gives you an exit code instead of making you go looking:

```bash
omarchy-toggle-enabled screensaver-off && echo "screensaver is off"
```

The flags are named for the off state — `screensaver-off`, `suspend-off`, `bar-off` — so their presence means the feature is disabled.

### Indicators in the bar

When a mode is on, you get a small glyph in the middle of the top bar next to the clock. That's the indicators widget, and it carries dictation, screen recording, pending reminders, night light, do not disturb, and stay awake.

Inactive indicators are hidden. Hover the area around them and they fade in dimmed, so you can click one to turn it on without knowing its hotkey. Clicking an active one turns it back off. If you'd rather see all of them all the time, set `alwaysShow` to `true` on the `omarchy.indicators` entry in `~/.config/omarchy/shell.json` — see [the top bar](05-the-top-bar.md) for how bar widgets are configured.

### Night light

`Super + Ctrl + N` warms the screen to 4000K, and hitting it again puts it back to 6500K. It's driven by hyprsunset, which the toggle starts for you if it isn't already running.

By default hyprsunset does nothing to your screen at all. `~/.config/hypr/hyprsunset.conf` ships with an identity profile precisely so the display stays untouched until you ask for warmth. If you'd rather have it switch by the clock, replace that with a time profile:

```
profile {
    time = 20:00
    temperature = 4000
}
```

Then start hyprsunset at login by adding `o.launch_on_start("hyprsunset")` to `~/.config/hypr/autostart.lua`. The 4000K/6500K pair used by the toggle is fixed, so the config file is where you go if you want a different temperature.

### Do not disturb

`Super + Ctrl + ,` silences notifications. No toasts pop up while it's on, and the crossed-out bell indicator sits in the bar to remind you why the desktop has gone quiet.

Nothing is lost, though. A silenced notification is written straight into your notification history, which is exactly the record you want when you come back and wonder what you missed. Open it with `Super + Shift + Alt + ,`. See [notices](10-notices.md) for the rest of the notification story.

Two kinds of message still get through: Maslow OS confirmation toasts for something you just did ("Theme changed", "Screenshot saved"), and critical alerts sent from the command line. Chat apps that mark everything critical to force their way in front of you don't qualify.

### Idle

The Omarchy shell owns idle behavior, and the timings are a top-level `idle` block in `~/.config/omarchy/shell.json`:

```json
{
  "version": 1,
  "idle": {
    "screensaver": 150,
    "lock": 300
  }
}
```

Both numbers are seconds counted from the moment you went idle — not from each other. So with the defaults, the screensaver comes up after two and a half minutes and the lock screen takes over at five minutes, whether or not the screensaver ran. Save the file and the shell picks up the new timings right away.

If you dismiss the screensaver before the lock deadline, that counts as activity and the pending lock is cancelled. You don't get locked out for glancing at your machine.

To stop locking on idle entirely, `Super + Ctrl + I` — or `omarchy toggle idle` — flips stay awake on, and the coffee cup indicator appears in the bar. That's the one to hit before a long presentation or a build you want to watch. Hit it again to go back to normal. `omarchy toggle idle status` prints the current state as JSON if you need it from a script.

This is about locking and the screensaver, not power. Suspend and hibernation have their own setup in [system sleep](36-system-sleep.md).

### The screensaver

The default screensaver is the Maslow screensaver. The Maslow mark sits in the middle of a dark navy screen, slowly breathing, with soft fields of brand-coloured light (pink, violet, teal and a touch of amber) drifting behind it. Small points of light flow through the mark's two bridges, from each lower circle up to the upper one, and gentle ripples spread out from the two standalone circles in turn. Under the mark are the MASLOW | AI-OS wordmark, a large clock showing hours and minutes, and a quiet "Press any key" hint, all lined up on one centre line. The whole picture wanders a little across the screen all the time, so nothing stays in exactly one place on your display. With more than one monitor, each one gets its own copy, and the light on each starts at a different point so neighbouring screens don't mirror each other.

Any key, mouse movement, click, or scroll dismisses it. Small bumps of the desk don't count — the mouse has to actually move a little before the screensaver goes away.

On battery it draws fewer frames, so it costs less power.

#### Motion

By default the screensaver follows the system Reduced Motion setting (_Trigger > Toggle > Reduced Motion_). With Reduced Motion on, it shows a still picture: no drifting light, no breathing, no flowing points or ripples, and no frames redrawn at all. Every five minutes the picture jumps to a slightly different spot, so a still screensaver still doesn't hold the same pixels for hours.

If you want the screensaver to behave differently from the rest of the system, set `screensaver.motion` in `~/.config/omarchy/shell.json`:

```json
"screensaver": {
  "style": "maslow",
  "motion": "full"
}
```

- `"auto"` (the default, also used when the value is missing or not recognised) follows the system Reduced Motion setting.
- `"full"` always animates the screensaver, even with Reduced Motion on everywhere else.
- `"reduced"` always shows the still picture, even with Reduced Motion off.

The shell picks up the change when you save the file.

You can start it on demand from _System > Screensaver_ (`Super + Esc`), which forces it up even if you've turned the idle screensaver off. There's no hotkey bound to it by default.

`omarchy toggle screensaver` is what turns the idle one off, if you'd rather go straight from working to locked.

### The classic screensaver

The classic style is ASCII art running through random text effects in a terminal, one instance per monitor. To switch to it, choose _Style > Screensaver > Classic_, or run:

```bash
omarchy screensaver style classic
```

`omarchy screensaver style maslow` switches back, and `omarchy screensaver style status` prints the style in use. The choice is saved as `"screensaver": { "style": "classic" }` in `~/.config/omarchy/shell.json`.

The classic style needs a terminal it knows how to configure — Alacritty, Foot, Ghostty, or Kitty — and will tell you so if your default terminal is something else. It is also what runs if the Maslow screensaver can't start, so you always get a screensaver.

Custom artwork applies to the classic style. Under _Style > Screensaver_ you can edit the text, or upload a png or svg and have it converted to ASCII. See [branding](41-branding.md).

### The lock screen

`Super + Ctrl + L` locks the machine. That runs the lock screen from the Omarchy shell, blanks the display, resets your keyboard layout to the first one so you're not typing your password in the wrong alphabet, and — if you have it running — locks 1Password on the way out.

The lock screen takes a password, and it'll take a fingerprint too once you've set one up. That, and the other ways to authenticate, are covered in [hardware authentication](37-hardware-authentication.md).
