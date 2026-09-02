# Security

Maslow OS is designed for real work on machines that can be lost, stolen, or exposed to untrusted networks. Its security model comes from Arch Linux, the compatible Omarchy engine, and Maslow-owned installation and update controls:

1. *Full-disk encryption is the default*: This is the most important step in protecting data on a lost or stolen computer. Maslow OS uses standard LUKS (Linux Unified Key Setup). An unencrypted installation is available only as an explicit choice for special-purpose systems.
2. *Firewall is enabled by default*: All incoming traffic is blocked by default except for port 53317 for [LocalSend](https://localsend.org/). Even ssh is off until you turn it on via _Setup > Security > SSHD_, which opens port 22 (rate limited against brute force) as part of the setup. We even lock down Docker access using the [ufw-docker](https://github.com/chaifeng/ufw-docker) setup to prevent that your containers are accidentally exposed to the world.
3. *Arch delivers current package updates*: Arch, the underlying distribution, is rolling. Security fixes become available through the normal Maslow OS Update route, which preserves the engine's snapshot, package, migration, and repair sequence.
4. *The engine uses controlled package sources*: The base engine uses Arch's core, extra, and multilib repositories plus the Omarchy package repository. Optional installers may use the AUR and identify that source during installation.
5. *Maslow presentation is repaired after engine updates*: The normal update lifecycle reapplies package-owned Maslow login, boot, menu, and metadata surfaces after compatible upstream changes without overwriting user menu overlays.

## Changing your passwords

You have two passwords on an encrypted install: the one that unlocks the drive at boot, and the one you log in and `sudo` with. Both can be changed under _Update > Password_ in the Maslow OS menu — _Drive Encryption_ for the first, _User_ for the second. Changing the drive password asks for the current one first, so have it handy.

## Passing on a machine you've already used

If you're handing your machine over to someone else, you don't have to reinstall it. Run _Setup > Reset Computer_ in the Maslow OS menu, type `reset` to confirm, and reboot. That wipes every user account and everything in `/home`, throws away all the packages and system changes you made since installation, and clears the machine's identity — network connections, host keys, and all. What comes back up is the setup wizard from the first boot, ready for its new owner to enter their own name, password, and encryption password.

It works by restoring the baseline snapshot the installer takes, so it's only available on machines installed from the Maslow OS ISO. On a drive without encryption, a reset is deletion rather than a secure erase; if the data was sensitive, perform a fresh install instead.

## Passwordless sudo

Sometimes you want `sudo` to stop asking, most often when an AI agent is doing a long stretch of system work for you. _Setup > Security > Passwordless Sudo_ turns that off for 15 minutes and then puts it back automatically. Run it again before the timer runs out to end it early, and pass your own number of minutes with `omarchy-sudo-passwordless 30` if 15 isn't enough.

Be clear-eyed about this one: while it's on, anything running as your user can do anything as root without being asked. That's the whole point, and it's also the whole risk.

## Release integrity

Omarchy engine packages retain their existing upstream keyring and verification path. Public Maslow OS releases require the separate Maslow-owned package-signing and publication process; development-preview ISOs are not public release artifacts until that process is ready.

Only download Maslow OS images from the release link shown in About or the product manifest, and verify them using the signature and key published with that exact release.
