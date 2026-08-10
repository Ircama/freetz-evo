# exiv2 0.28.8
  - Package: [master/make/libs/exiv2/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/exiv2/)
  - Homepage: [https://www.exiv2.org/](https://www.exiv2.org/)
  - Provides: `libexiv2.so` — Image metadata library
  - Used by: Gerbera (`FREETZ_PACKAGE_GERBERA_WITH_EXIV2`)
  - Externalization: supported
  - Toolchain: requires uClibc 1.0.58 or newer

Exiv2 is a C++ library for managing image metadata. It supports reading and writing Exif, IPTC, XMP, and ICC profiles in various image formats including JPEG, PNG, TIFF, and RAW formats.

Requires uClibc 1.0.58 or newer. Older uClibc versions (0.9.x, 1.0.14) fail
to compile exiv2 0.28.x because the upstream headers trigger
`-Werror=sign-compare` warnings, so the option is disabled on older
toolchains (`FREETZ_TARGET_UCLIBC_1_0_58`).