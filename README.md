# Maslow OS

Maslow OS is a Linux desktop for people who build and work with AI. It brings together everyday apps, developer tools, and guided AI setup in a Maslow-designed desktop.

Maslow OS is based on [Omarchy](https://omarchy.org/) and [Arch Linux](https://archlinux.org/). It keeps the Omarchy engine, commands, and extension compatibility.

> **In development:** `0.1.0-preview.1`. The current installer is an internal x86_64 preview. There is no public installer release yet.

## Which computers is it for?

The main target is **64-bit Intel and AMD PCs**, including laptops, desktops, and x86_64 virtual machines. **It is not Apple-only.**

`x86_64` describes the processor architecture, not the computer brand. Hardware still needs testing: a matching processor does not guarantee that every Wi-Fi adapter, graphics card, or other component works.

| Computer or environment | Current status |
| --- | --- |
| Intel/AMD PC with UEFI boot | Main installer target. A fresh installation has been tested on a Lenovo ThinkPad. |
| x86_64 virtual machine | Uses the same ISO. Use a disposable VM for preview testing. |
| Intel Mac | Can use the x86_64 ISO in a virtual machine. Installing directly on Mac hardware is not currently supported. |
| ARM64 computer, including Apple Silicon Macs | Not supported by this ISO. A separate ARM64 development preview exists, but there is no public ARM64 installer. |

## What's included?

- Chrome as the default browser.
- A dock and App Launcher, with **Super+A** to open the launcher.
- Codex, Claude Code, and Hermes preinstalled, with guided setup still being tested.
- Maslow dark and light themes, plus a Reduced Motion option.
- The Omarchy app-install and update tools.

Preinstalled AI tools still need configuration and provider sign-in. Signing in does not grant elevated permissions; those are separate choices.

## What has been tested?

On the September 5, 2026 preview, the Lenovo tester reported:

- A completed fresh installation and working desktop.
- Successful installs of figlet, VS Code, Tailscale, and Zen Browser **before any system update**.
- Chrome selected by default, the Maslow dock icon, and App Launcher opening with Super+A.
- Running the supported system update afterward.

This is progress on one machine, not a guarantee for every PC. Detailed post-update checks, plugin updates, AI setup, recovery, and performance measurements remain open. See the [test record and remaining checklist](docs/handoffs/2026-09-05-verified-usb-native-acceptance.md).

## Trying the preview

For now, contributors can follow the [ISO build instructions](https://github.com/letsgomaslow/maslow-os-iso) to build an internal test image. Do not redistribute preview images as a Maslow OS release. Public installers will appear on the [releases page](https://github.com/letsgomaslow/maslow-os/releases) when ready.

Use a spare compatible PC or a disposable x86_64 VM:

1. Back up anything important and verify the ISO checksum.
2. Write and verify a USB installer, or attach the ISO to a VM with UEFI enabled. Writing the USB erases its existing contents.
3. Boot the installer and check the installation disk carefully. **Installation can erase the selected disk.** Create your own account and password; there is no shared default password.
4. After installation, remove the USB or detach the ISO, then boot from the installed disk.

An Apple Silicon Mac cannot run this ISO natively. Emulation is a development-only path, not evidence of native hardware support or comparable performance.

## Updates

Use the desktop update action or run:

```bash
omarchy update
```

The preview temporarily holds back Maslow's desktop packages so upstream packages do not replace them. Other system packages can still update. Do not bypass this protection or switch update channels. A long-term Maslow update and recovery path is still being developed.

## Screenshots

Preview images; appearance may change.

![Maslow OS setup welcome screen](docs/images/maslow-os-setup-preview.png)

![Maslow OS desktop with the system bar and mountain sunrise background](docs/images/maslow-os-desktop.png)

## Help and contributing

- [Getting started](manual/02-getting-started.md)
- [Keyboard shortcuts](manual/07-hotkeys.md)
- [Themes](manual/06-themes.md)
- [Compatible Omarchy commands](manual/14-omarchy-cli.md)
- [Report a problem](https://github.com/letsgomaslow/maslow-os/issues)

Development is split across three repositories:

- **[maslow-os](https://github.com/letsgomaslow/maslow-os)** — desktop, commands, and defaults; product branch `main`.
- **[maslow-os-pkgs](https://github.com/letsgomaslow/maslow-os-pkgs)** — package recipes; product branch `maslow`.
- **[maslow-os-iso](https://github.com/letsgomaslow/maslow-os-iso)** — installer and ISO builds; product branch `maslow`.

Contributors should read [AGENTS.md](AGENTS.md), the [downstream maintenance guide](DOWNSTREAM.md), and the [testing guide](docs/testing.md). Keep source tests, native test results, and release readiness separate. A public release still needs verified install/update/recovery paths and Maslow-owned package signing and distribution.

## License and credits

The software retains the upstream [MIT License](LICENSE). See [NOTICE](NOTICE) for Omarchy attribution and the separate terms for Maslow names, logos, and brand assets.
