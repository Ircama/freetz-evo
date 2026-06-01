# tac 0.9.0

- Homepage: https://github.com/uutils/coreutils
- Changelog: https://github.com/uutils/coreutils/releases
- Repository: https://github.com/uutils/coreutils
- Package: ../../make/pkgs/tac/

tac is packaged from the upstream uutils/coreutils multi-call binary and installed
under the dedicated target-side command name `tac`.

## Build notes

- built from the upstream Rust coreutils source tree with only the `tac` utility enabled
- externalizable via the standard freetz external package flow