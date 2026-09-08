# Maslow OS wallpapers

`maslow-wallpaper-collage.png` is the approved four-panel wallpaper source supplied by the Maslow project owner on September 2, 2026 and revised on September 8, 2026 for the `Maslow | AI-OS` product lockup. The source is 2752×1536 with ten-pixel white dividers.

`branding/scripts/generate-assets` crops the four 1371×763 panels at the coordinates below, preserves the embedded Maslow Gradient Bridge and `Maslow | AI-OS` lockups, and performs a deterministic Lanczos resize with a centered edge crop to exact 3840×2160 WebP output.

| Output | Source crop |
|---|---:|
| `01-mountain-sunrise.webp` | `1371x763+0+0` |
| `02-canyon-storm.webp` | `1371x763+1381+0` |
| `03-aurora-lake.webp` | `1371x763+0+773` |
| `04-spiral-galaxy.webp` | `1371x763+1381+773` |

The four output files are byte-identical between `maslow-dark` and `maslow-light`, and the mountain sunrise is the first/default background by filename order. The September 8 revision removed the obsolete raster lockups with background reconstruction, then composited the approved Gradient Bridge SVG and licensed Manrope wordmark deterministically. Do not generatively redraw or approximate the embedded mark or wordmark; always use the canonical assets under `branding/logos/` and `branding/fonts/`.

The three additional 4K WebP sources are logo-free daily-desktop alternatives. The generator normalizes them to the same 3840×2160 output contract and copies identical results into both themes:

- `05-gradient-bridge-quiet-field.webp`
- `06-signal-over-water.webp`
- `07-topographic-ascent.webp`

These wallpapers are Maslow brand artwork and are outside the repository's MIT-licensed software, as described in `NOTICE`. Before public binary distribution, maintainers must confirm redistribution rights for every underlying photographic source.
