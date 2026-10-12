# libmatroska (Matroska container library) 1.7.1
  - Homepage: [https://github.com/Matroska-Org/libmatroska](https://github.com/Matroska-Org/libmatroska)
  - Changelog: [https://github.com/Matroska-Org/libmatroska/releases](https://github.com/Matroska-Org/libmatroska/releases)
  - Repository: [https://github.com/Matroska-Org/libmatroska](https://github.com/Matroska-Org/libmatroska)
  - Library: [master/make/libs/libmatroska/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libmatroska/)
  - Steward: -

libmatroska is a C++ library for handling Matroska container formats (MKV, MKA, MKS). Requires uClibc 1.0.58 or newer (libmatroska 1.7.1 sets CMAKE_CXX_STANDARD 14 in CMakeLists.txt, which the old GCC 4.6.4 toolchain does not support). Also depends on libebml, which has the same requirement.
