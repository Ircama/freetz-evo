# libsamplerate 0.2.2
  - Package: [master/make/libs/libsamplerate/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libsamplerate/)
  - Homepage: [https://github.com/libsndfile/libsamplerate](https://github.com/libsndfile/libsamplerate)
  - Provides: `libsamplerate.so` — Sample rate conversion library
  - Used by: `alsa-plugins` (optional, for samplerate plugin)
  - Externalization: supported

libsamplerate (also known as Secret Rabbit Code) is a sample rate conversion library for audio. It provides several converters with varying quality/performance trade-offs, from linear (fastest) to sinc-based (highest quality). Used by ALSA's samplerate plugin.