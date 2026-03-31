# QuickJS 2026-03-23 snapshot (binary only)
  - Homepage: [https://bellard.org/quickjs/](https://bellard.org/quickjs/)
  - Manpage: [https://bellard.org/quickjs/quickjs.html](https://bellard.org/quickjs/quickjs.html)
  - Changelog: [https://github.com/bellard/quickjs/commits/master/](https://github.com/bellard/quickjs/commits/master/)
  - Repository: [https://github.com/bellard/quickjs/](https://github.com/bellard/quickjs/)
  - Package: [master/make/pkgs/quickjs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/quickjs/)
  - Steward: -

------------

# QuickJS on Freetz

## Summary

QuickJS is a lightweight JavaScript engine and a useful alternative to Node.js on embedded targets.

## Package state

- Freetz package version format: `20260323`.
- Source is still pinned to a specific git commit via `_GIT_COMMIT`.
- Main binaries:
  - `qjs`
  - `qjsc` (optional if enabled)

## Externalization and size reporting

When the package is externalized, internal package size can appear as `0.00 kB`.

This is expected behavior:

- binaries are moved under `/mod/external/...`,
- internal filesystem paths become symlinks.

So `0.00 kB` means near-zero internal footprint, not missing binaries.

## Build notes

Current tree handling already includes:

- linking with `-latomic` for 64-bit atomic symbols on 32-bit targets,
- optional `fenv.h` handling via dedicated patching.

## Relevant files

- [make/pkgs/quickjs/quickjs.mk](../make/pkgs/quickjs/quickjs.mk)
- [make/pkgs/quickjs/Config.in](../make/pkgs/quickjs/Config.in)
- [make/pkgs/quickjs/external.in](../make/pkgs/quickjs/external.in)
- [make/pkgs/quickjs/external.files](../make/pkgs/quickjs/external.files)
