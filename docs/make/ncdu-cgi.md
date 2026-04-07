# ncdu CGI (disk usage web UI)
  - Package: [master/make/pkgs/ncdu-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ncdu-cgi/)
  - Steward: -
  - Depends on: `ncdu`
  - CGI: `/usr/lib/cgi-bin/ncdu.cgi`
  - Configuration URL: `http://fritz.box:81/cgi-bin/conf/ncdu`

`ncdu-cgi` provides an interactive web frontend for `ncdu` in Freetz.
It runs `ncdu` in JSON export mode and renders results as an expandable tree or a flat table view.

## Main features

- Scan selected paths with server-side validation
- Tree view and flat view (`Flat view (all objects)`)
- Sorting by `dsize`, `asize`, `uid`, `gid`, `mtime`
- Toggle sort order (ascending/descending)
- Optional scan flags:
  - follow symlinks (`-L`)
  - stay on one filesystem (`-x`)
- Context actions on selected entries:
  - open selected directory
  - expand/collapse
  - copy path
  - delete entry (with safety checks)
- Debug log panel (`/tmp/ncdu-cgi.log`) and last scan dump metadata

## Security model

The CGI applies path checks before running destructive or scan actions:

- absolute path only
- traversal patterns denied (`..`)
- allowed prefixes restricted (e.g. `/var/media/ftp`, `/var/media`, `/var/mod`, `/tmp`, `/mod`)
- delete allowed only inside the current scan root

## Backend invocation

The scanner uses `ncdu` with JSON output, equivalent to:

```sh
ncdu -0 --exclude-kernfs --exclude-caches -e -o- <scan-path>
```

The CGI wraps JSON in Freetz-compatible HTML response format and the frontend extracts/parses the payload in browser-side JavaScript.
