# xclock 1.1.1
  - Homepage: [https://www.x.org/](https://www.x.org/)
  - Package: [master/make/pkgs/xclock/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/xclock/)
  - Steward: -

## Build notes

- **Forced `LDFLAGS=-lm`**: xclock's `configure.ac` uses `AC_SEARCH_LIBS(sincos, [m], ...)` to detect `-lm`. The old GCC 4.6.4 toolchain treats `sin`/`cos`/`sincos` as builtins, so the search never adds `-lm` and the link fails with undefined references to `sin`/`cos`. Forcing `LDFLAGS="$(TARGET_LDFLAGS) -lm"` in `$(PKG)_CONFIGURE_ENV` fixes it. This is a GCC-version-specific quirk, not uClibc-specific, so a configure-env workaround is used instead of a gate (no regression on any toolchain).

