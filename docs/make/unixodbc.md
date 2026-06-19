# unixODBC 2.3.12 (tools)
  - Homepage: [https://www.unixodbc.org/](https://www.unixodbc.org/)
  - Changelog: [https://github.com/lurcher/unixODBC/releases](https://github.com/lurcher/unixODBC/releases)
  - Repository: [https://github.com/lurcher/unixODBC](https://github.com/lurcher/unixODBC)
  - Package: [master/make/pkgs/unixodbc/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/unixodbc/)
  - Steward: -

  - Provides: `libodbc.so.2.0.0`, `libodbcinst.so.2.0.0`, `libodbccr.so.2.0.0`
  - Externalization: supported

unixODBC provides the ODBC driver-manager runtime used by target software that
talks to SQL backends through the standard ODBC interface.

## Runtime interface

- `libodbc` driver manager
- `libodbcinst` installer/configuration helper library
- `libodbccr` cursor helper library
- headers and `odbc_config` kept in staging for cross-build consumers

## Freetz-EVO build scope

- shared libraries enabled
- no GUI tools
- no bundled database drivers
- iconv and readline support disabled to keep the dependency footprint small