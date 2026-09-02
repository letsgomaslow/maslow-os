# Development Tools

## Alternative Editors

Maslow OS ships with [Neovim](https://neovim.io/) by default. For a different editor, open the Maslow OS menu (`Super + Space`) and browse _Install > Editor_. VS Code, Cursor, Zed, Sublime Text, Helix, Vim, and Emacs are listed there. If your editor is not listed, try _Install > Package_ and then _Install > AUR_.

Theme matching is offered for `VSCode`, `Cursor`, `VSCodium`, and `Helix`.

You can set the system-wide default editor under `Setup > Defaults > Editor`.

## Environment

Maslow OS supports a broad set of development environments through _Install > Development_ in the Maslow OS menu (`Super + Space`). Options include Ruby on Rails; Node.js, Bun, and Deno; Laravel and Symfony; Go, Rust, Python, Java, Elixir with Phoenix, .NET, OCaml, Zig, Clojure, and Scala.

The majority of these environments are managed by [Mise](https://mise.jdx.dev/). It's a tool that lets you install and run multiple versions of a programming language on the same machine. It's like rbenv or rvm for Ruby or virtualenv for Python, but it works for a bunch of different environments.

To install, say, Ruby, you'd run `mise use -g ruby`, which will both install Ruby and set it as the global default. Or, if your project has a .ruby-version file, you can just run `mise i` in the root of that project.

## Docker

[Docker](https://www.docker.com/) hardly needs any introduction. It allows you to run isolated containers, and Omarchy installs everything needed to run it well, including Docker itself and [Docker Compose](https://docs.docker.com/compose/).

By default your user is *not* in the `docker` group. That group is effectively passwordless root — anything in it can `docker run -v /:/host` and take over the machine — so a single rogue script or dependency running as you would otherwise be one command away from root. So on the command line you run Docker with `sudo` (`sudo docker ps`, `sudo docker compose up`), and the graphical tools that talk to the daemon — the Docker TUI on `Super + Shift + D` and the Windows VM — ask for authorization when they need it. If you want the convenience of a groupless setup back and understand the tradeoff, enable it from **Setup > Security > Sudoless Docker** (or run `omarchy-setup-security-sudoless-docker`), which adds you to the `docker` group after a warning; then plain `docker` and the `d` alias work without `sudo` again.

Remember to checkout the Lazydocker command to manage your containers in a cool TUI using `Super + Shift + D`; it asks for authorization the first time unless you have enabled sudoless Docker.

You can setup the common databases for local development in Docker using _Install > Development > Docker DB_ in the Maslow OS menu.

## GitHub CLI

[The GitHub CLI](https://cli.github.com/) let's you authenticate with your GitHub account and clone private repositories using it. It's wired up as one of the lazy-loading mise stubs, so the first time you run `gh`, it installs itself. To authenticate, run `gh auth login`. Then you can checkout private repositories using `gh repo clone org/repo`.

You can also perform a bunch of other GitHub operations using this command. Just run `gh` to see everything that's possible.

There's a lazy-installing stub for `ghui` for managing your pull requests in a TUI too. And [lazygit](https://github.com/jesseduffield/lazygit) is preinstalled, if you'd like to drive git itself from a TUI as well.
