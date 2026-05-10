# lf r41 (binary only)
  - Homepage: [https://github.com/gokcehan/lf](https://github.com/gokcehan/lf)
  - Manpage: [https://github.com/gokcehan/lf/blob/master/doc.md](https://github.com/gokcehan/lf/blob/master/doc.md)
  - Changelog: [https://github.com/gokcehan/lf/releases](https://github.com/gokcehan/lf/releases)
  - Repository: [https://github.com/gokcehan/lf](https://github.com/gokcehan/lf)
  - Package: [master/make/pkgs/lf/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/lf/)
  - Steward: Ircama

`lf` (List Files) is a terminal file manager written in Go, inspired by `ranger` but with a simpler
codebase and faster startup. It uses a Miller-column layout (similar to macOS Finder) with a left
panel for the parent directory, a centre panel for the current directory, and a right panel for a
file preview. Navigation, copying, moving, renaming, and custom commands are driven entirely from
the keyboard; the key bindings can be fully remapped in `~/.config/lf/lfrc`.

The Freetz-EVO package cross-compiles the upstream Go sources into a single self-contained binary
for the selected target architecture (MIPS softfloat, ARM, x86, AArch64).

## Runtime details in Freetz

- Binary path: `/usr/bin/lf`
- Runtime dependencies: none (self-contained CGO_ENABLED=0 binary)
- Externalization: supported for the binary
- Typical storage location: any writable path; configuration file should be placed at
  `~/.config/lf/lfrc` (e.g. on a USB or NAS volume and symlinked from `/root`)

## Build notes

- Built with Go cross-compilation and `CGO_ENABLED=0`, producing a statically-linked binary.
- The upstream version string is embedded via `-ldflags="-X main.gVersion=r41"` so
  `lf --version` reports the correct tag.
- The package shares the Freetz-EVO Go host toolchain (Go 1.25.10) used by `lazygit`, `gh`,
  `fzf`, `caddy`, and other Go-based packages.
- No network access is required during the build: the upstream source tarball is self-contained.

## Typical usage

```sh
lf
```

Start `lf` in the current directory. Use arrow keys (or `h`/`j`/`k`/`l`) to navigate,
`Enter` to open a file or enter a directory, `q` to quit.

### Basic key bindings (defaults)

| Key | Action |
|-----|--------|
| `j` / `↓` | move down |
| `k` / `↑` | move up |
| `h` / `←` | go to parent directory |
| `l` / `→` / `Enter` | open / enter directory |
| `gg` | go to top |
| `G` | go to bottom |
| `d` | cut selection |
| `y` | yank (copy) selection |
| `p` | paste |
| `r` | rename |
| `D` | delete |
| `/` | search |
| `q` | quit |

### Example lfrc snippet

Store this at `~/.config/lf/lfrc` (or the path pointed to by `$XDG_CONFIG_HOME/lf/lfrc`):

```sh
# Use rifle-style previewer for common formats
set previewer ~/.config/lf/preview.sh
set cleaner  ~/.config/lf/clean.sh

# Show hidden files by default
set hidden true

# Sort directories first
set dirfirst true
```

Notes:
- `lf` is best used over an SSH session; colours and box-drawing characters render correctly in
  any UTF-8-capable terminal (e.g. PuTTY, Kitty, iTerm2, Windows Terminal).
- The binary is stripped at build time, keeping it well under 10 MB on MIPS.
