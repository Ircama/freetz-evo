# Node.js 18.20.8
  - Homepage: [https://nodejs.org/](https://nodejs.org/)
  - Manpage: [https://nodejs.org/docs/latest/api/](https://nodejs.org/docs/latest/api/)
  - Changelog: [https://github.com/nodejs/node/releases](https://github.com/nodejs/node/releases)
  - Repository: [https://github.com/nodejs/node](https://github.com/nodejs/node)
  - Package: [master/make/pkgs/nodejs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nodejs/)

------------

# Node.js on Freetz (MIPS32)

## Summary

For MIPS32 targets in this tree, the practical choice is Node.js 18.x.

## V8 and MIPS32

- Node.js 18 is the last line that is generally workable on MIPS32.
- Starting from Node.js 19+, practical V8 support for MIPS32 is no longer maintained in a reliable way.
- Some configure options may still exist, but real-world support is oriented to mips64 and mips64el.
- Result: for MIPS32 targets, staying on Node.js 18 is the recommended path.

## Host build issue: bits/c++config.h

Typical failure:

- fatal error: bits/c++config.h: No such file or directory

Observed cause:

- generated host makefiles under `out/tools/v8_gypfiles/*.host.mk` may contain both `-m64` and `-m32`.
- on host systems without 32-bit C++ multilib headers, host-side V8 helper builds fail.

Applied fix:

- in [make/pkgs/nodejs/nodejs.mk](../make/pkgs/nodejs/nodejs.mk), generated `.host.mk` files are sanitized before build to:
  - remove leaked target staging include/library paths,
  - remove host `-m32` flags.

This keeps host compilation aligned with the actual host toolchain and avoids accidental 32-bit C++ header dependencies.

## OpenSSL note

- OpenSSL 3.0 remains the stable default choice.
- OpenSSL 3.5 can be used as an experimental variant.
