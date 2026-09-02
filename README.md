# Maslow OS

Maslow OS is an opinionated Linux environment for AI builders and operators. It combines a focused desktop, practical developer tooling, and a coherent Maslow interface so teams can move from an AI roadmap to working systems without losing clarity or control.

Maslow OS is based on [Omarchy](https://omarchy.org/) and [Arch Linux](https://archlinux.org/). The Omarchy command line, configuration paths, package names, and extension contracts remain intact for compatibility.

> **Preview status:** `0.1.0-preview.1`. The current Apple Silicon image is a development preview, not a supported public ARM release. The first supported installer target is x86_64.

## Product branches

- `quattro` is a clean, fast-forward-only mirror of upstream Omarchy.
- `maslow` is the downstream integration branch.
- `main` is the default public product branch.
- Upstream updates flow from `quattro` into `maslow`, then into `main` through reviewed pull requests. Public product history is never rebased or force-pushed.

The maintained downstream patch inventory and sync procedure live in [`DOWNSTREAM.md`](DOWNSTREAM.md).

## Maslow themes

Maslow OS includes two first-party themes:

- `maslow-dark` — the installation default, built on Maslow dark navy.
- `maslow-light` — an accessible light companion using Maslow's approved text accents.

Both themes generate native Omarchy configurations for Hyprland, the shell, terminals, browsers, btop, Neovim, Helix, VS Code, Obsidian, and related applications. The **Reduced Motion** toggle disables Hyprland animation and applies theme backgrounds without a transition.

## Documentation

The inherited Omarchy manual remains the authoritative reference for engine behavior and the compatible `omarchy` commands. Maslow-specific branding, release, and downstream maintenance guidance lives in this repository.

- [Getting Started](manual/02-getting-started.md)
- [Omarchy CLI compatibility](manual/14-omarchy-cli.md)
- [Themes](manual/06-themes.md)
- [Branding](manual/41-branding.md)
- [Making a theme](manual/43-making-your-own-theme.md)

## Verification

Run brand and source checks inside Linux with Bash 5:

```bash
./test/maslow-brand
./test/cli
./test/shell
./test/all
```

Graphical acceptance tests must run in a disposable VM through the sibling ISO repository. See [`agents/skills/acceptance-tests.md`](agents/skills/acceptance-tests.md).

## License and attribution

The software remains available under the upstream [MIT License](LICENSE). See [`NOTICE`](NOTICE) for upstream attribution and the separate treatment of Maslow names, logos, and brand assets.
