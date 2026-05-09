# rclone 1.74.1 (cloud storage sync)
  - Homepage: [https://github.com/rclone/rclone](https://github.com/rclone/rclone)
  - Manpage / README: [https://rclone.org/docs/](https://rclone.org/docs/)
  - Changelog: [https://github.com/rclone/rclone/releases](https://github.com/rclone/rclone/releases)
  - Repository: [https://github.com/rclone/rclone](https://github.com/rclone/rclone)
  - Package: [../../make/pkgs/rclone/](../../make/pkgs/rclone/)
  - Steward: Ircama

`rclone` is a command-line tool for syncing and managing files across many cloud
storage backends as well as local and network paths.

## Runtime details in Freetz

- Binary path: `/usr/bin/rclone`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary
- Typical storage location: keep configuration, cache, and transfer staging areas on writable storage

## Build notes

- The package cross-compiles the upstream Go sources into a single executable.
- No extra shared libraries are required on the target for the core binary.

## Typical usage

```sh
RCLONE_CONFIG=/var/media/ftp/uStor01/rclone/rclone.conf \
  rclone ls remote:
```

Notes:
- Credentials and tokens should be stored outside the firmware image.
- For long-running transfers, use external storage for caches and temp files.