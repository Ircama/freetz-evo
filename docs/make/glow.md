# glow 2.1.2 (binary only)
  - Homepage: [https://github.com/charmbracelet/glow](https://github.com/charmbracelet/glow)
  - Manpage: [https://github.com/charmbracelet/glow#usage](https://github.com/charmbracelet/glow#usage)
  - Changelog: [https://github.com/charmbracelet/glow/releases](https://github.com/charmbracelet/glow/releases)
  - Repository: [https://github.com/charmbracelet/glow](https://github.com/charmbracelet/glow)
  - Package: [master/make/pkgs/glow/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/glow/)
  - Steward: Ircama
  - Manpage / README: [https://github.com/charmbracelet/glow#readme](https://github.com/charmbracelet/glow#readme)

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