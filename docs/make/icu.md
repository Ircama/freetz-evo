# ICU 76.1
  - Package: [master/make/libs/icu/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/icu/)
  - Homepage: [https://icu.unicode.org/](https://icu.unicode.org/)
  - Provides: `libicui18n.so`, `libicuuc.so`, `libicudata.so` (plus `icudt76b.dat`) — Unicode internationalization
  - Used by: `gerbera`
  - Externalization: supported (icudt76b.dat is ~31 MB, externalized by default)

ICU (International Components for Unicode) provides robust and full-featured Unicode and locale support. Uses `--with-data-packaging=archive` (`.dat` file mode) for cross-compilation compatibility.