# jsoncpp 1.9.8
  - Package: [master/make/libs/jsoncpp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/jsoncpp/)
  - Homepage: [https://github.com/open-source-parsers/jsoncpp](https://github.com/open-source-parsers/jsoncpp)
  - Provides: `libjsoncpp.so` — JSON reader/writer
  - Used by: —
  - Externalization: supported

jsoncpp is a C++ library for interacting with JSON data, providing intuitive serialization and deserialization with minimal overhead.

## Build notes

- Requires uClibc 1.0.58 or newer (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): jsoncpp 1.9.8 uses the C++11 feature `cxx_delegating_constructors` in `src/lib_json/CMakeLists.txt` (`target_compile_features`), which the old GCC 4.6.4 toolchain does not support, so the CMake configure fails. The new toolchain (GCC 13.4 + uClibc 1.0.58) supports it.