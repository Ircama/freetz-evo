# libuv (libuv.so) 1.44.2/1.53.0
  - Homepage: [https://libuv.org/](https://libuv.org/)
  - Manpage: [https://docs.libuv.org/en/v1.x/](https://docs.libuv.org/en/v1.x/)
  - Changelog: [https://github.com/libuv/libuv/releases](https://github.com/libuv/libuv/releases)
  - Repository: [https://github.com/libuv/libuv](https://github.com/libuv/libuv)
  - Library: [master/make/libs/libuv/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libuv/)
  - Steward: -

libuv is a async IO library for various programs Requires uClibc 1.0.58 or newer: on GCC <= 5 toolchains (uClibc 0.9.x-1.0.14) libuv 1.44.2 is built, which uses pthread_atfork. uClibc only provides pthread_atfork as a hidden static-only symbol, so any program linking libuv.so fails with "undefined reference to pthread_atfork". On uClibc 1.0.58+ (GCC > 5) libuv 1.52.1 is used, which no longer calls pthread_atfork.
