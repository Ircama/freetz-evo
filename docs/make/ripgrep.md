# ripgrep 14.1.1

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
