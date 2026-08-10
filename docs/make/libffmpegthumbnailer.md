# libffmpegthumbnailer 2.2.3
  - Package: [master/make/libs/libffmpegthumbnailer/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libffmpegthumbnailer/)
  - Homepage: [https://github.com/dirkvdb/ffmpegthumbnailer](https://github.com/dirkvdb/ffmpegthumbnailer)
  - Provides: `libffmpegthumbnailer.so` — Video thumbnail generator
  - Used by: `gerbera`
  - Externalization: supported
  - Toolchain: requires uClibc 1.0.58 or newer

libffmpegthumbnailer is a lightweight library for generating thumbnails from video files, using FFmpeg for frame extraction and scaling.

Requires uClibc 1.0.58 or newer. It uses C++11 `std::to_string`/
`std::stoi`, which the old uClibc toolchains (0.9.x, 1.0.14) do not
provide (libstdc++ disables them when `_GLIBCXX_USE_C99` is not defined
for the C library), so the option is disabled on older toolchains
(`FREETZ_TARGET_UCLIBC_1_0_58`).