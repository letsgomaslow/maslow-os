# Dotfiles

Maslow OS is primarily configured through dotfiles in `~/.config`; those are your files. Files in `/usr/share/omarchy` belong to the compatible engine packages and should not be edited directly. Override their values in `~/.config` instead.

The key configs can be edited straight from the Maslow OS menu (`Super + Space`), like _Setup > Monitors_, _Setup > Keybindings_, _Setup > Input_, and _Setup > Config > [file]_. When you do it this way, any process that needs restarting after config edits automatically will be after you quit the editor (Neovim by default — `:wq`, remember! — but you can change that via _Setup > Defaults > Editor_).

Here's a list of the key files in `~/.config` and what they control:

| File                  | Purpose              |
| ----------------------- | --------------------- |
| `~/.config/hypr/hyprland.lua` | The main Hyprland config. Loads the Omarchy defaults plus your override files below. [Learn more about Hyprland configs](https://wiki.hypr.land/Configuring/).  |
| `~/.config/hypr/bindings.lua` | Your own keybindings and overrides of the defaults. |
| `~/.config/hypr/monitors.lua` | Controls your monitors, resolution, and position. |
| `~/.config/hypr/input.lua` | Controls your keyboard layout, mouse, and trackpad settings. |
| `~/.config/hypr/looknfeel.lua` | Controls gaps, borders, animations, and the rest of the look. |
| `~/.config/hypr/autostart.lua` | Controls extra processes started with the session. |
| `~/.config/omarchy/shell.json` | Controls the Omarchy shell: bar position, layout, and widgets, plus screensaver, lock, and idle timings. |
| `~/.config/foot/foot.ini` | Controls your terminal (foot is the default). |
| `~/.XCompose` | Defines your quick-access emoji and name/email autocomplete. Make sure to run `omarchy-restart-xcompose` after making changes. |

If you end up making a lot of changes to tweak your own setup, it's a good idea to backup all these dotfiles. [Stow is a great way to do that](https://www.youtube.com/watch?v=NoFiYOqnC4o).

### Starting your own apps with the session

If you want something to run every time you log in — a sync daemon, a chat app, your own script — put it in `~/.config/hypr/autostart.lua`:

```lua
o.launch_on_start("my-service")
```

That starts the command as part of the session, so it's properly cleaned up when you log out again.

### Running scripts on system events

Omarchy fires hooks at a handful of moments, and you can hang your own scripts off them. They live in `~/.config/omarchy/hooks/<event>.d/`, one directory per event, and every executable file in there runs when the event happens:

| Event | When it runs |
| ----- | ------------ |
| `post-boot` | Right after the desktop has started |
| `post-update` | During `omarchy update`, after packages and migrations |
| `pre-refresh-pacman` | Before `omarchy refresh pacman` re-syncs the package config |
| `theme-set` | After a theme change (theme name in `$1`) |
| `font-set` | After a font change (font name in `$1`) |
| `battery-low` | When the battery gets low (percentage in `$1`) |

Each of those directories already holds a `.sample` file showing the shape of a hook — drop the `.sample` from the name to put it to work. To install a script you've written elsewhere, use `omarchy hook install post-boot ~/my-hook`, which copies it in and makes it executable.

### Adding your own menu entries

The Maslow OS menu (`Super + Space`) can be extended with your own rows by editing `~/.config/omarchy/extensions/omarchy-menu.jsonc`. Entries are keyed by a dotted id, and the id is what places them in the tree, so `personal` shows up on the root menu and `personal.notes` shows up inside it:

```jsonc
"personal": {"icon":"","label":"Personal"},
"personal.notes": {"icon":"󰎞","label":"Notes","action":"omarchy-launch-editor ~/notes"},
```

Reuse an existing id and you override that row instead of adding a new one. The file ships with all the available fields documented as comments.

### Adding your own shell exports, functions, and aliases

Maslow OS ships with ergonomic aliases and helper functions, and you can add your own aliases, functions, and exports in `~/.bashrc`. This file is not overwritten on updates. You can also override engine defaults safely here.

### Changing internal engine files

Look, this is your computer. You can do whatever you want with it, but I would advise against making changes to the files in `/usr/share/omarchy` directly. They belong to the Omarchy pacman package, so your changes will simply be overwritten on the next update. You're better off just overwriting any default values you don't like in the `~/.config/*` folder instead.

You can change just about everything that way, like the default keybindings. Just edit `~/.config/hypr/bindings.lua` to, say, replace [Obsidian](https://obsidian.md/) with [Joplin](https://joplinapp.org/) (install with `omarchy-pkg-add joplin-bin`):

```
hl.unbind("SUPER + SHIFT + O")
o.bind("SUPER + SHIFT + O", "Joplin", "joplin-desktop")
```

If you insist on hacking on the internal Omarchy files, switch to the dev channel via _Update > Channel > Dev_. That links Omarchy to a git checkout of the source code in `~/omarchy`, which you're free to change to your heart's content. Ain't nobody here to tell you what to do!

### Resetting any changes

If you end up making a mess of the configurations, you can always revert them to the defaults via _Update > Config_ in the Maslow OS menu. Or by running `omarchy reinstall configs` to reset everything.
