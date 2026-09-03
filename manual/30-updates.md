# Updates

Maslow OS and your packages are kept up to date through _Maslow OS Update_ in the Maslow OS menu (`Super + Space`) or the compatible `omarchy update` command.

Maslow OS uses the Omarchy engine and preserves its update ordering. One update can include Maslow presentation changes, [Omarchy engine releases](https://github.com/basecamp/omarchy/releases), migrations, Arch system packages from the [Omarchy Arch Mirror](https://github.com/omacom-io/omarchy-mirror), and [AUR](https://aur.archlinux.org/) packages. [Maslow OS release notes](https://github.com/letsgomaslow/maslow-os/releases) and engine notes are labeled separately before the update starts.

When updates are available, a circle arrow icon appears to the right of your clock. Click it to open Maslow OS Update. If a required step fails, the update is labeled unfinished and retains the actual failure status so it can be corrected and retried.

![update-available](images/update-available.webp)

### Four channels

The Omarchy engine is delivered along four compatible channels: stable, RC, edge, and dev. New installations start on the stable channel, which tracks the [official engine releases](https://github.com/omacom/omarchy/releases/), as well as the [stable Omarchy Arch mirror](https://github.com/omacom-io/omarchy-mirror) that's running one month behind the latest, so we can catch incompatibilities that require downstream presentation repairs before they cause problems for people.

But if you'd like to help spot those potential issues, you can run on the edge channel. That keeps the engine packages on the latest development builds and lets you update to the latest Arch packages as soon as they're available. You should only do this if you're experienced with Linux and know how to recover a system that has problems.

Before any new major release, we'll be doing final validation using the RC channel. If you're interested in helping with final polishing, come hang out in #omarchy-release-candidates on the Discord.

Finally, there's the dev channel, which links the engine directly to a git checkout of the source code in `~/omarchy`, combined with the edge packages. You should only use this channel if you're an experienced Linux user, working directly on the Omarchy engine, and willing to tolerate breakage.

You can switch between channels using _Update > Channel_ from the Maslow OS menu (or `omarchy-channel-set` in the terminal).

### Firmware updates

Your packages aren't the only thing that goes stale. Many laptops and peripherals ship BIOS, SSD, and dock firmware through the Linux Vendor Firmware Service, and _Update > Firmware_ in the Maslow OS menu will fetch and install whatever your hardware has waiting. It installs `fwupd` the first time you run it. Plenty of firmware can only be written during a reboot, so don't be surprised to be asked for one.

### Warning about direct pacman/yay updates

If you're already familiar with Arch, you might be tempted to just run `pacman -Syu` or `yay -Syu` yourself, but if you do that, you'll miss the snapshot, engine migrations, Maslow branding repair, and configuration updates that run together with new packages. That's why Maslow OS stops a direct system upgrade and points you to `omarchy update` instead. (If you really know what you're doing, the guard will tell you how to bypass it for a single transaction.)

### Rolling back bad updates

If you ever have a problem after doing an update, you can rollback your system to the snapshot taken before the update. Just restart and pick the snapshot in the boot loading menu from before you started the update.

![bootloader](images/bootloader.webp)

If your configuration files have been corrupted, you can perform a Maslow OS repair using the compatible `omarchy reinstall` command. It reinstalls the default engine packages, returns the engine to stable, downgrades packages that are too new, resets packaged configuration, and reruns Maslow branding repair. Your changes to package-owned defaults are overwritten; user-owned menu overlays remain separate.
