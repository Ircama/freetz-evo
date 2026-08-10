# spdlog 1.17.0
  - Package: [master/make/libs/spdlog/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/spdlog/)
  - Homepage: [https://github.com/gabime/spdlog](https://github.com/gabime/spdlog)
  - Provides: `libspdlog.so` — Fast C++ logging library
  - Used by: `gerbera`
  - Externalization: supported
  - Toolchain: requires uClibc 1.0.58 or newer

spdlog is a very fast, header-only/compiled C++ logging library. Built with `-DSPDLOG_FMT_EXTERNAL=ON` to use the external libfmt instead of bundling its own.

Requires uClibc 1.0.58 or newer (it depends on libfmt, which is also
gated on the same toolchain).