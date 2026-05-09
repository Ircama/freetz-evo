# age 1.3.1 (binaries only)
  - Homepage: [https://github.com/FiloSottile/age](https://github.com/FiloSottile/age)
  - Manpage: [https://github.com/FiloSottile/age#usage](https://github.com/FiloSottile/age#usage)
  - Changelog: [https://github.com/FiloSottile/age/releases](https://github.com/FiloSottile/age/releases)
  - Repository: [https://github.com/FiloSottile/age](https://github.com/FiloSottile/age)
  - Package: [master/make/pkgs/age/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/age/)
  - Steward: Ircama
  - Manpage / README: [https://github.com/FiloSottile/age#readme](https://github.com/FiloSottile/age#readme)

`age` is a modern file encryption tool designed as a small and auditable alternative
to traditional OpenPGP workflows. The Freetz-EVO package installs both `age` for
encryption and `age-keygen` for key generation.

## Runtime details in Freetz

- Binary paths: `/usr/bin/age`, `/usr/bin/age-keygen`
- Runtime dependency profile: self-contained Go binaries built with `CGO_ENABLED=0`
- Externalization: supported for both binaries

## Build notes

- The package is cross-compiled with the shared Freetz-EVO Go host toolchain.
- No target-side shared Go runtime or libc add-ons are required beyond the base system.

## Typical usage

```sh
age-keygen -o /var/media/ftp/uStor01/keys/age.txt
age -r age1... -o backup.tar.age backup.tar
```

Notes:
- Store private keys on writable storage, not in the read-only firmware image.
- `age` works well for scripted backups and secret-file handling on USB or NAS-backed paths.