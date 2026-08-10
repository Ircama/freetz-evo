# ripgrep 15.1.0
  - Toolchain: requires uClibc 1.0.58 or newer
  - Homepage: [https://github.com/BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep)
  - Manpage: [https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
  - Changelog: [https://github.com/BurntSushi/ripgrep/releases](https://github.com/BurntSushi/ripgrep/releases)
  - Repository: [https://github.com/BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep)
  - Package: [master/make/pkgs/ripgrep/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ripgrep/)
  - Steward: -

- Homepage: https://github.com/BurntSushi/ripgrep
- Changelog: https://github.com/BurntSushi/ripgrep/releases
- Repository: https://github.com/BurntSushi/ripgrep
- Package: ../../make/pkgs/ripgrep/

ripgrep is a fast recursive search tool based on Rust regular-expression engines.

In this port it is provided as target-side binary `rg` for quick code/config searches
on the device filesystem.

## Build notes

- built with Rust/Cargo cross toolchain integration
- optimized for freetz target architectures
