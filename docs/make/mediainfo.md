# MediaInfo 25.10
  - Homepage: [https://mediaarea.net/en/MediaInfo](https://mediaarea.net/en/MediaInfo)
  - Manpage: [https://mediaarea.net/en/MediaInfo](https://mediaarea.net/en/MediaInfo)
  - Changelog: [https://github.com/MediaArea/MediaInfo/releases](https://github.com/MediaArea/MediaInfo/releases)
  - Repository: [https://github.com/MediaArea/MediaInfo](https://github.com/MediaArea/MediaInfo)
  - Package: [master/make/pkgs/mediainfo/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/mediainfo/)
  - Steward: Ircama
  - Toolchain: requires GCC 4.7 or newer (`FREETZ_TARGET_GCC_4_7_MIN` in `Config.in`): MediaInfoLib compiles with `-std=c++11` (`AM_CXXFLAGS` in `Makefile.am`), which the old GCC 4.6.4 toolchain does not recognize (`cc1plus: error: unrecognized command line option '-std=c++11'`). This is a GCC issue, not uClibc-specific: uClibc 1.0.14 with GCC 5.5 builds fine, so a uClibc gate would be a regression.
