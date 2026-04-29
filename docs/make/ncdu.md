# ncdu 1.19 (disk usage analyzer)
  - Homepage: [https://dev.yorhel.nl/ncdu](https://dev.yorhel.nl/ncdu)
  - Manpage: [https://linux.die.net/man/1/ncdu](https://linux.die.net/man/1/ncdu)
  - Changelog: [https://dev.yorhel.nl/ncdu/changes](https://dev.yorhel.nl/ncdu/changes)
  - Repository: [https://code.blicky.net/yorhel/ncdu](https://code.blicky.net/yorhel/ncdu)
  - Package: [master/make/pkgs/ncdu/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ncdu/)
  - Steward: Ircama
`ncdu` (NCurses Disk Usage) is a fast terminal disk usage analyzer.
It scans directory trees and provides an interactive ncurses UI to find the biggest files/directories quickly.

## Runtime details in Freetz

- Binary path: `/usr/bin/ncdu`
- Main dependency: `libncurses`
- Typical data roots: `/var/media/ftp`, `/var/media`, `/mod`

## Typical usage

```sh
ncdu /var/media/ftp
```

```sh
ncdu -x /var/media/ftp
```

```sh
ncdu -0 -o- /var/media/ftp > /tmp/ncdu-export.json
```

Notes:
- `-x` keeps the scan on one filesystem.
- `-0 -o-` exports JSON to stdout (used by `ncdu-cgi`).
