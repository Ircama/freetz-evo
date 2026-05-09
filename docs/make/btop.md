# btop 1.4.7
  - Homepage: [https://github.com/aristocratos/btop](https://github.com/aristocratos/btop)
  - Manpage: [https://github.com/aristocratos/btop#readme](https://github.com/aristocratos/btop#readme)
  - Changelog: [https://github.com/aristocratos/btop/releases](https://github.com/aristocratos/btop/releases)
  - Repository: [https://github.com/aristocratos/btop](https://github.com/aristocratos/btop)
  - Package: [master/make/pkgs/btop/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/btop/)
  - Steward: -
  - Manpage / README: [https://github.com/aristocratos/btop#readme](https://github.com/aristocratos/btop#readme)

`btop` is a modern terminal monitor for CPU, memory, disks, network traffic, and processes.
The Freetz-EVO package follows the lightweight `htop`-style binary packaging model and installs a single stripped binary plus optional upstream themes.

## Runtime details in Freetz

- Binary path: `/usr/bin/btop`
- Optional themes: `/usr/share/btop/themes`
- Main runtime dependencies: `libstdc++`, `libpthread`, `libm`
- Externalization: supported for the binary and, if enabled, the themes directory

## Build notes

- Upstream currently expects a C++23-capable toolchain, so the package depends on GCC 13 in Freetz.
- A compatibility patch replaces `std::ranges::to` usage and avoids `quick_exit()` issues on the `uClibc` + `libstdc++` target combination.
- GPU support is disabled because FRITZ!Box targets do not provide a GPU backend.

## Typical usage

```sh
btop
```

You can switch themes inside the program if `FREETZ_PACKAGE_BTOP_THEMES` is enabled in `make menuconfig`.