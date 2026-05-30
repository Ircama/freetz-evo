# LMDB 0.9.33
  - Homepage: [https://www.symas.com/lmdb/](https://www.symas.com/lmdb/)
  - Changelog: [https://github.com/LMDB/lmdb/releases](https://github.com/LMDB/lmdb/releases)
  - Repository: [https://github.com/LMDB/lmdb](https://github.com/LMDB/lmdb)
  - Package: [../../make/libs/lmdb/](../../make/libs/lmdb/)

  - Provides: `liblmdb.so`
  - Externalization: supported

LMDB is a compact memory-mapped key/value store library with copy-on-write
semantics and very low runtime overhead.

## Typical consumers

- PowerDNS LMDB backend
- target packages needing a small embedded database without a separate daemon

## Notes

The Freetz-EVO recipe builds and installs only the shared library runtime; the
CLI tools and documentation are intentionally omitted from the target package.