# caps 0.9.26
  - Package: [master/make/libs/caps/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/caps/)
  - Provides: `libcaps.so` — C++ thread-safe container library
  - Used by: —
  - Externalization: supported

The `caps` library provides a collection of C++ thread-safe container classes and utilities. It is a dependency for the CAPS LADSPA plugin suite, providing reusable data structures for audio processing pipelines.

## Build notes

- **Patch `010-fix-exp10f-uclibc.patch`** (`dsp/v4f_IIR2.h`): uClibc (all versions, including uClibc-ng 1.0.58) does not declare `exp10f` in `<math.h>`, so the `__APPLE__`-only fallback in caps leaves `'exp10f' was not declared in this scope` errors when compiling on uClibc toolchains. The patch adds `<math.h>` and provides `exp10f` via `powf(10.0f, f)` when `__UCLIBC__` is defined. glibc is unaffected (native `exp10f` declaration is used).