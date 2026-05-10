# nmon 16s (binary only)
  - Homepage: [https://nmon.sourceforge.io/](https://nmon.sourceforge.io/)
  - Manpage: [https://nmon.sourceforge.io/pmwiki.php?n=Site.Documentation](https://nmon.sourceforge.io/pmwiki.php?n=Site.Documentation)
  - Changelog: [https://nmon.sourceforge.io/pmwiki.php?n=Site.Download](https://nmon.sourceforge.io/pmwiki.php?n=Site.Download)
  - Repository: [https://sourceforge.net/projects/nmon/files/](https://sourceforge.net/projects/nmon/files/)
  - Package: [master/make/pkgs/nmon/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nmon/)
  - Steward: Ircama

`nmon` is a full-screen curses-based performance monitor for Linux systems.
It shows CPU usage, memory pressure, disks, filesystems, network activity,
kernel counters, and process statistics in real time, and it can also record
periodic performance samples to a CSV-like capture file for later analysis.

The Freetz-EVO package builds upstream `lmon16s.c` directly into a single
target binary and installs it as `/usr/bin/nmon`.

## Runtime details in Freetz

- Binary path: `/usr/bin/nmon`
- Main runtime dependencies: `libncurses`, `libm`
- Externalization: supported for the binary
- Typical usage: interactive terminal sessions over SSH, serial console, or a local shell on the box

## Build notes

- Upstream ships `nmon` as a single C source file (`lmon16s.c`), so the Freetz package uses a small custom unpack step instead of a traditional tarball build system.
- The binary is linked against the Freetz `ncurses` package, matching the upstream `<ncurses.h>` include and keeping the dependency chain small.
- On MIPS targets, the package enables the generic Linux code paths that upstream only activates for `X86` and `ARM` builds.
- The unused upstream include of `<fstab.h>` is removed during the build because it is not provided by the current Freetz uClibc target environment.

## Typical usage

Interactive mode:

```sh
nmon
```

Common interactive keys:

| Key | Action |
|-----|--------|
| `c` | CPU statistics |
| `m` | memory statistics |
| `d` | disk statistics |
| `n` | network statistics |
| `t` | top processes |
| `h` | help |
| `q` | quit |

Capture performance data to file:

```sh
nmon -f -s 30 -c 120
```

This writes 120 samples at 30-second intervals to an `nmon` output file in the current directory.

Notes:
- `nmon` is primarily a keyboard-driven monitoring tool and is best used in an SSH terminal with a reasonably wide screen.
- For long captures, prefer running it from writable external storage so the generated output files do not consume internal flash space.
- The captured files can be reviewed later with spreadsheets, parsers, or the upstream nmon analysis tooling on another machine.