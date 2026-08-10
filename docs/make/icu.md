# ICU 76.1
  - Package: [master/make/libs/icu/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/icu/)
  - Homepage: [https://icu.unicode.org/](https://icu.unicode.org/)
  - Provides: `libicui18n.so`, `libicuuc.so`, `libicudata.so` (plus `icudt76b.dat`) — Unicode internationalization
  - Used by: `gerbera`, `mpd`
  - Externalization: supported (icudt76b.dat is ~31 MB, externalized by default)
  - Toolchain: requires uClibc 1.0.58 or newer

ICU (International Components for Unicode) provides robust and full-featured Unicode and locale support. Uses `--with-data-packaging=archive` (`.dat` file mode) for cross-compilation compatibility.

Requires uClibc 1.0.58 or newer. ICU 76.x uses C++17 `auto` non-type
template parameters that the old GCC toolchains (uClibc 0.9.x, 1.0.14)
cannot compile, so the option is disabled on older toolchains
(`FREETZ_TARGET_UCLIBC_1_0_58`).