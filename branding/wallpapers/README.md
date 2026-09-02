# Maslow OS wallpapers

`maslow-wallpaper-collage.png` is the approved four-panel wallpaper source supplied by the Maslow project owner on September 2, 2026. The source is 2752×1536 with ten-pixel white dividers.

`branding/scripts/generate-assets` crops the four 1371×763 panels at the coordinates below, preserves the embedded Maslow Gradient Bridge lockups, and performs a deterministic Lanczos resize with a centered edge crop to exact 3840×2160 WebP output.

| Output | Source crop |
|---|---:|
| `01-mountain-sunrise.webp` | `1371x763+0+0` |
| `02-canyon-storm.webp` | `1371x763+1381+0` |
| `03-aurora-lake.webp` | `1371x763+0+773` |
| `04-spiral-galaxy.webp` | `1371x763+1381+773` |

The four output files are byte-identical between `maslow-dark` and `maslow-light`, and the mountain sunrise is the first/default background by filename order. Do not use generative editing to redraw the embedded mark, wordmark, scenery, or composition.

These wallpapers are Maslow brand artwork and are outside the repository's MIT-licensed software, as described in `NOTICE`. Before public binary distribution, maintainers must confirm redistribution rights for every underlying photographic source.
