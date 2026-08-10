# FFmpeg 5.1.4/7.1.1
  - Homepage: [https://www.ffmpeg.org/](https://www.ffmpeg.org/)
  - Manpage: [https://www.ffmpeg.org/documentation.html](https://www.ffmpeg.org/documentation.html)
  - Changelog: [https://www.ffmpeg.org/index.html#news](https://www.ffmpeg.org/index.html#news)
  - Repository: [https://git.ffmpeg.org/ffmpeg.git](https://git.ffmpeg.org/ffmpeg.git)
  - Package: [master/make/pkgs/ffmpeg/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ffmpeg/)
  - Steward: -
  - Versions: 5.1.4 (older toolchains) / 7.1.1 (uClibc 1.0.58 or newer)

FFmpeg 7.1.1 is only selectable on toolchains with uClibc 1.0.58 or
newer: its configure requires C11 static assertions (`static_assert`
from `<assert.h>`), which older uClibc versions do not provide. On
toolchains with older uClibc, the version choice automatically falls
back to FFmpeg 5.1.4 (`FREETZ_PACKAGE_FFMPEG_VERSION_ABANDON`).

