# vhs 0.11.0 (binary only)
  - Toolchain: requires uClibc 1.0.58 or newer (auto-selects ttyd, which needs libuv and fails to link on older uClibc with "undefined reference to pthread_atfork")
  - Homepage: [https://github.com/charmbracelet/vhs](https://github.com/charmbracelet/vhs)
  - Manpage: [https://github.com/charmbracelet/vhs#readme](https://github.com/charmbracelet/vhs#readme)
  - Changelog: [https://github.com/charmbracelet/vhs/releases](https://github.com/charmbracelet/vhs/releases)
  - Repository: [https://github.com/charmbracelet/vhs](https://github.com/charmbracelet/vhs)
  - Package: [master/make/pkgs/vhs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/vhs/)
  - Steward: Ircama
  - Manpage / README: [https://github.com/charmbracelet/vhs#readme](https://github.com/charmbracelet/vhs#readme)

`vhs` records scripted terminal sessions into media output from declarative tape
files, which is useful for demos and CLI documentation.

## Runtime details in Freetz

- Binary path: `/usr/bin/vhs`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package builds the upstream Go sources into a single executable.
- Practical recording workflows may require extra helper tools expected by upstream, especially `ffmpeg`; these are not pulled in automatically by the package.

## Typical usage

```sh
vhs /var/media/ftp/uStor01/vhs/demo.tape
```

Notes:
- Recording output and temporary assets should be written to external storage.
- On small embedded targets, keep tape files and output sizes conservative.