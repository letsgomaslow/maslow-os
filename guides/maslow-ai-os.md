# Using the Maslow AI-OS preview

Maslow AI-OS builds on Omarchy and Arch Linux. The [engine manual](../manual/01-welcome-to-omarchy.md) retains Omarchy's name, credits, commands, and documentation. Read this guide first for Maslow's preview availability, AI features, support, and hardware limits. An upstream download or installation recommendation is not a Maslow release or a hardware acceptance result.

## Installation and hardware

Maslow's current installer is an internal x86_64 preview for compatible Intel and AMD PCs. There is no public Maslow installer release yet. Follow [Trying the preview](../README.md#trying-the-preview) for image verification and installation precautions; public installers will appear on the [Maslow releases page](https://github.com/letsgomaslow/maslow-os/releases) when ready.

Back up important data before testing an installer. A full-disk installation erases the selected disk. Remove the installer after installation and confirm that the installed disk boots independently. Test a fresh application installation before the first system update.

An emulated x86_64 VM tests software behavior; it does not establish that a physical Intel Mac's graphics, Wi-Fi, audio, sleep, or recovery work. Direct installation on Intel Mac hardware has not been accepted for this preview. Keep macOS until those checks and a verified backup and recovery plan are complete. The upstream Mac chapter's compatibility claims and historical performance example describe Omarchy, not tested Maslow compatibility. Apple Silicon cannot run this x86_64 installer natively.

## Hub and Voice

Maslow Hub has six sections: Home, Work, Connections, My context, Apps, and Settings. AI tools being installed is separate from their readiness: configuration, provider sign-in, permissions, and successful task completion each need their own check.

Press **Super+H** to open Maslow Voice. Voice uses the supported Codex, Claude Code, and Hermes handoffs. Provider authentication stays in each provider's own flow, and elevated permissions require a separate choice. A working Voice panel does not prove microphone, speaker, provider, or completed-agent-task acceptance.

Use **Super+A** for the App Launcher. Maslow includes dark and light themes and a Reduced Motion option. Omarchy command names and configuration paths remain compatible; use the engine manual for desktop navigation and configuration.

## Updates and recovery

Use the desktop update action or `maslow update`; the compatible `omarchy update` path also works. Keep the temporary Maslow desktop package hold in place. A held runtime package and an available Arch update are different parts of the preview update path. Do not bypass the hold or switch channels to try to force a desktop update.

System snapshots cover the system root. Home data and user state can remain newer after restoring a snapshot. Keep separate backups of personal files, and check app and account readiness after recovery. A successful VM restore does not prove encrypted recovery or recovery on your physical computer.

## Support

Report product issues to [Maslow AI-OS Support](https://github.com/letsgomaslow/maslow-os/issues). Use the [Omarchy community](https://omarchy.org/discord) for upstream engine questions. Include the tested version and whether the result came from a VM or physical hardware, and leave credentials and private logs out of reports.
