# Neovim 0.12.2
  - Homepage: [https://neovim.io/](https://neovim.io/)
  - Manpage: [https://neovim.io/doc/](https://neovim.io/doc/)
  - Changelog: [https://github.com/neovim/neovim/releases](https://github.com/neovim/neovim/releases)
  - Repository: [https://github.com/neovim/neovim](https://github.com/neovim/neovim)
  - Package: [master/make/pkgs/neovim/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/neovim/)
  - Steward: Ircama
  - Toolchain: requires GCC 4.9 or newer (`FREETZ_TARGET_GCC_4_9_MIN` in `Config.in`): the bundled libuv uses `<stdatomic.h>` (C11 atomics), which the old GCC 4.6.4 toolchain does not provide (`fatal error: stdatomic.h: No such file or directory`). This is a GCC issue, not uClibc-specific: uClibc 1.0.14 with GCC 5.5 builds fine.

