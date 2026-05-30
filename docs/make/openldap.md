# OpenLDAP 2.6.8 (client libraries)
  - Homepage: [https://www.openldap.org/](https://www.openldap.org/)
  - Changelog: [https://www.openldap.org/software/release/changes.html](https://www.openldap.org/software/release/changes.html)
  - Repository: [https://git.openldap.org/openldap/openldap](https://git.openldap.org/openldap/openldap)
  - Package: [../../make/pkgs/openldap/](../../make/pkgs/openldap/)

  - Provides: `liblber.so.2.200.0`, `libldap.so.2.200.0`
  - Externalization: supported

This package bundles the OpenLDAP client-side shared libraries used by target
software that needs LDAP protocol access without shipping the full slapd server.

## Runtime interface

- `liblber` for BER encoding/decoding helpers
- `libldap` for LDAP client connections and operations
- public headers installed only in staging for cross-build consumers

## Freetz-EVO build scope

- client libraries only
- no slapd server
- no overlays or database backends
- TLS and Cyrus SASL disabled in this lean runtime package