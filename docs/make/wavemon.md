# wavemon 0.9.7 (wireless monitor)
  - Homepage: [https://github.com/uoaerg/wavemon](https://github.com/uoaerg/wavemon)
  - Manpage / README: [https://github.com/uoaerg/wavemon#readme](https://github.com/uoaerg/wavemon#readme)
  - Changelog: [https://github.com/uoaerg/wavemon/releases](https://github.com/uoaerg/wavemon/releases)
  - Repository: [https://github.com/uoaerg/wavemon](https://github.com/uoaerg/wavemon)
  - Package: [../../make/pkgs/wavemon/](../../make/pkgs/wavemon/)
  - Steward: Ircama

`wavemon` is an ncurses-based monitoring tool for wireless interfaces.
It shows signal level, bitrate, channel, traffic counters, and device-specific link statistics directly in a terminal UI.

## Runtime details in Freetz

- Binary path: `/usr/bin/wavemon`
- Main runtime dependencies: `libncursesw`, `libnl`, `libpthread`, `libm`
- Externalization: supported for the binary

## Build notes

- The package is built from the upstream autoconf project.
- `libcap` support is disabled with `--without-libcap` to keep the target dependency chain small.
- `libnl` is packaged separately in Freetz-EVO and provides the netlink libraries required by `wavemon`.

## Typical usage

```sh
wavemon
```

Notes:
- `wavemon` is useful on targets exposing wireless interfaces and netlink statistics.
- On devices without a usable Wi-Fi interface the program still starts, but it has no relevant wireless data to display.