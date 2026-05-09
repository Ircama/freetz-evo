# glow 2.1.2 (Markdown renderer)
  - Homepage: [https://github.com/charmbracelet/glow](https://github.com/charmbracelet/glow)
  - Manpage / README: [https://github.com/charmbracelet/glow#readme](https://github.com/charmbracelet/glow#readme)
  - Changelog: [https://github.com/charmbracelet/glow/releases](https://github.com/charmbracelet/glow/releases)
  - Repository: [https://github.com/charmbracelet/glow](https://github.com/charmbracelet/glow)
  - Package: [../../make/pkgs/glow/](../../make/pkgs/glow/)
  - Steward: Ircama

`glow` renders Markdown documents directly in the terminal, making README files and
notes easy to browse on the box without a browser.

## Runtime details in Freetz

- Binary path: `/usr/bin/glow`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package cross-compiles the upstream Go sources into a single executable.
- No extra target-side rendering libraries are needed for the default terminal output mode.

## Typical usage

```sh
glow /var/media/ftp/uStor01/docs/README.md
```

Notes:
- `glow` is useful for browsing local package notes, changelogs, and Markdown-based documentation over SSH.
- The terminal theme and width affect the rendered output, as in upstream usage.