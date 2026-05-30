# tinycdb 0.81
  - Homepage: [https://www.corpit.ru/mjt/tinycdb.html](https://www.corpit.ru/mjt/tinycdb.html)
  - Package: [../../make/libs/tinycdb/](../../make/libs/tinycdb/)

  - Provides: `libcdb.so.1`
  - Externalization: supported

tinycdb is a small implementation of Dan Bernstein's constant database format
for read-mostly key/value lookups.

## Typical consumers

- PowerDNS tinydns backend
- software that needs compact constant-database access on target

## Notes

This package installs the shared `libcdb` runtime, the public `cdb.h` header in
staging, and a generated `libcdb.pc` file for cross-build consumers.