# restic 0.18.1 (backup tool)
  - Homepage: [https://github.com/restic/restic](https://github.com/restic/restic)
  - Manpage / README: [https://restic.readthedocs.io/en/stable/](https://restic.readthedocs.io/en/stable/)
  - Changelog: [https://github.com/restic/restic/releases](https://github.com/restic/restic/releases)
  - Repository: [https://github.com/restic/restic](https://github.com/restic/restic)
  - Package: [../../make/pkgs/restic/](../../make/pkgs/restic/)
  - Steward: Ircama

`restic` is a secure backup tool with repository integrity checks, deduplication,
encryption, and support for local or remote storage backends.

## Runtime details in Freetz

- Binary path: `/usr/bin/restic`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary
- Typical storage location: repository, cache, and password files should live on writable media

## Build notes

- The package is built from upstream Go sources with the `disable_grpc_modules` tag to keep the dependency footprint smaller.
- The resulting binary is self-contained and suitable for SSH-driven backup jobs.

## Typical usage

```sh
RESTIC_REPOSITORY=/var/media/ftp/uStor01/restic/repo \
RESTIC_PASSWORD_FILE=/var/media/ftp/uStor01/restic/password.txt \
  restic snapshots
```

Notes:
- The repository can be local, remote, or layered on top of tools such as `rclone`.
- Backups and cache directories should not be placed on the internal read-only firmware image.