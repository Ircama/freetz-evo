# ncmpcpp 0.10.1
  - Homepage: [https://github.com/ncmpcpp/ncmpcpp](https://github.com/ncmpcpp/ncmpcpp)
  - Changelog: [https://github.com/ncmpcpp/ncmpcpp/releases](https://github.com/ncmpcpp/ncmpcpp/releases)
  - Repository: [https://github.com/ncmpcpp/ncmpcpp](https://github.com/ncmpcpp/ncmpcpp)
  - Package: [master/make/pkgs/ncmpcpp/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/ncmpcpp/)
  - Steward: -

  - Depends on: `libmpdclient`, `ncursesw`, `curl`, `taglib`
  - Build-only dependencies: Boost (date_time, system, filesystem, thread, program_options, regex, atomic) — statically linked
  - Provides: `/usr/bin/ncmpcpp`
  - Externalization: supported

`ncmpcpp` is a feature-rich ncurses-based MPD client and a successor/alternative to `ncmpc`. It extends the classic MPD client experience with a tag editor, media library browser, advanced playlist management, search functionality, clock display, configurable outputs screen, and a built-in audio visualizer.

## Freetz integration

- intended companion to the local `mpd` package, but can control any reachable MPD server
- useful for interactive SSH sessions and direct terminal usage on the device
- compiled with taglib, curl, clock, outputs, and visualizer support enabled
- externalizable to move the binary out of internal flash

## Build characteristics

- Autotools build system with Boost bundled as a build-time dependency
- The package downloads and cross-compiles Boost 1.87.0 (static libraries only: date_time, system, filesystem, thread, program_options, regex, atomic) as a build prerequisite
- Boost locale support is explicitly disabled (patched out of configure.ac) to avoid ICU dependencies
- Configured with `--enable-static --disable-shared` and linked statically against Boost
- Unicode support disabled for compatibility with the target's ncursesw configuration
- Visualizer, clock, and outputs screens enabled