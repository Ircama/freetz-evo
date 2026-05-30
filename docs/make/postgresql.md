# PostgreSQL 16.3
  - Homepage: [https://www.postgresql.org/](https://www.postgresql.org/)
  - Changelog: [https://www.postgresql.org/docs/release/](https://www.postgresql.org/docs/release/)
  - Repository: [https://git.postgresql.org/gitweb/?p=postgresql.git](https://git.postgresql.org/gitweb/?p=postgresql.git)
  - Package: [../../make/pkgs/postgresql/](../../make/pkgs/postgresql/)

  - Provides: `libpq.so.5.16`
  - Externalization: supported

This package exports the PostgreSQL client runtime (`libpq`) used by target-side
software that needs PostgreSQL connectivity and can optionally install a minimal
server toolset on target (`postgres`, `pg_ctl`, `initdb`).

## Runtime interface

- shared `libpq` client library runtime on target
- optional server binaries: `postgres`, `pg_ctl`, `initdb`
- `libpq-fe.h` and related headers in staging only
- suitable for consumers such as PowerDNS `gpgsql`

## Freetz-EVO build scope

- client library always built
- server components selectable via package options
- GSSAPI, LDAP, ICU, XML, XSLT, OpenSSL, readline, and zlib disabled to keep
  the package small and dependency-light