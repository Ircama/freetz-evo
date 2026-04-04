# Node.js 18.20.8
  - Homepage: [https://nodejs.org/](https://nodejs.org/)
  - Manpage: [https://nodejs.org/docs/latest/api/](https://nodejs.org/docs/latest/api/)
  - Changelog: [https://github.com/nodejs/node/releases](https://github.com/nodejs/node/releases)
  - Repository: [https://github.com/nodejs/node](https://github.com/nodejs/node)
  - Package: [master/make/pkgs/nodejs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nodejs/)
  - Steward: -

------------

## Build note

Node.js recompilation is a multi-core operation that keeps the host system busy for many hours and requires significant RAM; the number of parallel jobs in the submake has been reduced to keep resource consumption manageable.

## V8 and MIPS32

- Node.js 18 is the last line that is generally workable on MIPS32.
- Starting from Node.js 19+, practical V8 support for MIPS32 is no longer maintained in a reliable way.
- Some configure options may still exist, but real-world support is oriented to mips64 and mips64el.
- Result: for MIPS32 targets, staying on Node.js 18 is the recommended path.
