# libXt 1.3.0
  - Package: [master/make/libs/libXt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libXt/)
  - Homepage: [https://www.x.org/](https://www.x.org/)
  - Provides: `libXt.so` — X Toolkit Intrinsics library
  - Used by: `libXaw`, `libXmu`
  - Externalization: supported

libXt is the X Toolkit Intrinsics library, providing the foundation for the Xt widget system used by Xaw and other X11 widget sets.

## Build notes

- **`ac_cv_c_undeclared_builtin_options='none needed'`**: the autoconf 2.70+ `AC_C_UNDECLARED_BUILTIN` test fails on the old GCC 4.6.4 toolchain (it cannot report undeclared builtins even with `-fno-builtin`), so the cache variable is forced in `$(PKG)_CONFIGURE_ENV`. Same pattern as `flac`/`glib2`/`apr-util`. This is a GCC-version-specific issue, not uClibc-specific, so a configure-env workaround is used instead of a gate (no regression on any toolchain).