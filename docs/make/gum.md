# gum 0.17.0 (binary only)
  - Homepage: [https://github.com/charmbracelet/gum](https://github.com/charmbracelet/gum)
  - Manpage: [https://github.com/charmbracelet/gum#readme](https://github.com/charmbracelet/gum#readme)
  - Changelog: [https://github.com/charmbracelet/gum/releases](https://github.com/charmbracelet/gum/releases)
  - Repository: [https://github.com/charmbracelet/gum](https://github.com/charmbracelet/gum)
  - Package: [master/make/pkgs/gum/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/gum/)
  - Steward: Ircama
  - Manpage / README: [https://github.com/charmbracelet/gum#readme](https://github.com/charmbracelet/gum#readme)

`gum` provides reusable terminal UI primitives for shell scripts, such as prompts,
choices, formatted output, confirmation dialogs, and progress indicators.

## Runtime details in Freetz

- Binary path: `/usr/bin/gum`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The Freetz-EVO package builds only the main `gum` executable.
- It is intended for interactive shell workflows and custom maintenance scripts on the target.

## Typical usage

```sh
gum choose start stop status
```

Notes:
- `gum` is especially handy for small shell frontends stored on USB or NAS media.
- The package does not pull in any separate theme assets or helper scripts.