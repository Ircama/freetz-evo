# lame 3.100
  - Homepage: [https://lame.sourceforge.io/](https://lame.sourceforge.io/)
  - Repository: [https://svn.code.sf.net/p/lame/svn/trunk/lame](https://svn.code.sf.net/p/lame/svn/trunk/lame)
  - Package: [master/make/libs/lame/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/lame/)
  - Steward: -

  - Provides: `libmp3lame.so.0` shared runtime
  - Externalization: supported

LAME (LAME Ain't an MP3 Encoder) is a high-quality MPEG Audio Layer 3 (MP3) encoding library. In Freetz-EVO, it is packaged as a shared library providing `libmp3lame.so` for target-side applications that need MP3 encoding capabilities.

## Runtime interface

- shared library `libmp3lame.so.0.0.0` plus SONAME symlinks
- ABI-compatible runtime for MP3 encoding applications on the target
- headers and `pkg-config` metadata installed only in staging for cross-build consumers

## Freetz integration

- packaged as a standalone shared library for MP3 encoding
- the LAME frontend (`lame` CLI tool) is disabled in this build to keep the package lean; only the library is installed
- externalizable to move the shared object out of internal flash

## Build characteristics

- Autotools build with shared and static library enabled
- frontend (`lame` CLI binary) explicitly disabled