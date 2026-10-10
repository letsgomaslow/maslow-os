# Maslow OS CLI

Maslow OS is usually controlled through the hotkeys and the Maslow OS menu (`Super + Space`). From a terminal, use `maslow` — for example `maslow update` or `maslow theme list`. It runs exactly the same commands as the compatible engine's `omarchy` CLI, which stays available along with its package names and paths so upstream tools and extensions continue to work. The CLI is particularly helpful when you're having an AI agent work with you on customization or configuration.

The CLI has access to all the internal tooling that is used both via the menu and otherwise. You can see everything that's available by running `maslow` in the terminal.

It looks something like this:

```
~ ❯ maslow
Maslow OS command center

Usage:
  maslow <command> [args...]
  maslow commands [--all] [--json] [--check]
  maslow <group> --help
  maslow <group> <command> --help

Common commands:
  maslow update              Update Maslow OS and system packages
  maslow theme list          List available themes
  maslow theme set <name>    Apply a theme
  maslow font list           List available fonts
  maslow screenshot          Take a screenshot
  maslow debug               Print debugging information

Groups:
  agent          AI coding agent usage data
  audio          Audio input and output controls
  bar            Maslow OS bar layout and settings
  battery        Battery status helpers
  bluetooth      Bluetooth device controls
  branch         Omarchy git branch management
  branding       About and screensaver branding
  brightness     Display and keyboard brightness
  capture        Screenshots and screen recording
  channel        Omarchy release channel management
  clipboard      Clipboard helpers
  cmd            Command and shortcut helpers
  config         System configuration helpers
  debug          Diagnostics and support logs
  ...
```

And you can dive deeper on every group:

```
~ ❯ omarchy capture
Capture commands — Screenshots and screen recording:
  omarchy capture qr                                                                                                                                                                                                       Decode a QR code from a screenshot region
  omarchy capture screenrecording [--fullscreen] [--with-desktop-audio] [--with-microphone-audio] [--with-webcam] [--webcam-device=<device>] [--webcam-size=<small|medium|large>] [--resolution=<size>] [--stop-recording]  Start or stop screen recording
  omarchy capture screenrecording with webcam                                                                                                                                                                              Pick a webcam and start a screen recording with it
  omarchy capture screenshot [smart|region|windows|fullscreen] [slurp|copy|save] [--editor=<name>]                                                                                                                         Take a screenshot
  omarchy capture text                                                                                                                                                                                                     Extract text from a screenshot region with OCR
  omarchy capture webcam resize <smaller|larger|reset|small|medium|large>                                                                                                                                                  Resize the active webcam recording overlay
```

Every command takes `--help` too, whether you ask a whole group (`omarchy capture --help`) or a single command (`omarchy capture screenshot --help`).

### Opening the menu from the terminal

The Maslow OS menu is scriptable as well, which is handy for your own keybindings. `omarchy menu` opens it at the root, and you can jump straight to any point in the tree by naming it: `omarchy menu summon style.theme` goes right to the theme picker, `omarchy menu toggle system` opens the system menu and closes it again if it's already up, and `omarchy menu close` puts it away.
