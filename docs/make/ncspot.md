# ncspot 1.3.4
  - Homepage: [https://github.com/hrkfdn/ncspot](https://github.com/hrkfdn/ncspot)
  - Changelog: [https://github.com/hrkfdn/ncspot/releases](https://github.com/hrkfdn/ncspot/releases)
  - Repository: [https://github.com/hrkfdn/ncspot](https://github.com/hrkfdn/ncspot)
  - Package: [master/make/pkgs/ncspot/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ncspot/)
  - Steward: -
  - Toolchain: requires uClibc 1.0.58 or newer

- Homepage: https://github.com/hrkfdn/ncspot
- Changelog: https://github.com/hrkfdn/ncspot/releases
- Repository: https://github.com/hrkfdn/ncspot
- Package: ../../make/pkgs/ncspot/

- Depends on: `rust-host`, `openssl`, `alsa-lib`
- Provides: `/usr/bin/ncspot`
- Build profile: Rust/Cargo cross-build with target linker/ar wiring
- Enabled features: `alsa_backend`, `crossterm_backend` (default features disabled)
- Externalization: supported

`ncspot` is a terminal Spotify client based on librespot. The freetz recipe builds
it from upstream Rust sources and keeps the target build lean by disabling desktop
integrations that usually pull in DBus/notification backends.
