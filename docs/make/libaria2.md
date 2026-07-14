# libaria2 (external only)
  - Package: [master/make/libs/libaria2/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/libaria2/)
  - Provides: `libaria2.so.0.0.0` — aria2 download library
  - Used by: `ariang`
  - Externalization: external-only (symlink from FREETZ_LIBRARY_DIR)

libaria2 is the shared library component of the aria2 download utility, providing download functionality for HTTP(S), FTP, SFTP, BitTorrent, and Metalink protocols. This package is external-only — the library is provided as a symlink from the external library directory.