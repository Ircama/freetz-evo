# SQLite 3.40.1/3.47.1/3.53.3 (binary only)
  - Homepage: [https://www.sqlite.org](https://www.sqlite.org)
  - Manpage: [https://www.sqlite.org/docs.html](https://www.sqlite.org/docs.html)
  - Changelog: [https://www.sqlite.org/changes.html](https://www.sqlite.org/changes.html)
  - Repository: [https://www.sqlite.org/src/timeline](https://www.sqlite.org/src/timeline)
  - Package: [master/make/pkgs/sqlite/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/sqlite/)
  - Steward: [@fda77](https://github.com/fda77)

## Source variants

- `abandon`: `3.40.1` from `https://www.sqlite.org/2022/sqlite-autoconf-3400100.tar.gz` (`2c5dea207fa508d765af1ef620b637dcb06572afa6f01f0815bd5bbf864b33d9`)
- `stable`: `3.47.1` from `https://www.sqlite.org/2024/sqlite-autoconf-3470100.tar.gz` (`416a6f45bf2cacd494b208fdee1beda509abda951d5f47bc4f2792126f01b452`)
- `current`: `3.53.1` from `https://www.sqlite.org/2026/sqlite-autoconf-3530100.tar.gz` (`83e6b2020a034e9a7ad4a72feea59e1ad52f162e09cbd26735a3ffb98359fc4f`)

## Build Notes

Freetz EVO keeps three selectable SQLite tracks and merges them with the current upstream package layout:

- `3.40.1` remains the oldest compatibility branch.
- `3.47.1` is preserved locally as the last `stable` branch.
- `3.53.1` becomes the `current` upstream branch.

The older `3.40.1` and `3.47.1` builds still use the classic libtool `.libs/` output layout, while `3.53.1` emits the CLI and shared library directly in the source root. The local patch set still adds the pthread/GNU-source flags expected by Freetz, relaxes `-Ofast` to `-O2`, and preserves the cross-build compatibility fixes carried in this tree.

## Externalization
Both the SQLite CLI (`sqlite3`) and the library (`libsqlite3.so`) can be externalized:
- Binary: `/usr/bin/sqlite3` (~328 KB)
- Library: `/usr/lib/freetz/libsqlite3.so.x.x.x` with the exact SONAME depending on the selected branch (`0.8.6` for the old tracks, `3.53.1` for the current track)
