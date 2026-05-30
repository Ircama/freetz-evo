# libsodium 1.0.20
  - Homepage: [https://libsodium.org/](https://libsodium.org/)
  - Changelog: [https://github.com/jedisct1/libsodium/releases](https://github.com/jedisct1/libsodium/releases)
  - Repository: [https://github.com/jedisct1/libsodium](https://github.com/jedisct1/libsodium)
  - Package: [../../make/libs/libsodium/](../../make/libs/libsodium/)

  - Provides: `libsodium.so.26.2.0`
  - Externalization: supported

libsodium is a modern cryptographic library focused on safe high-level APIs for
common primitives such as Ed25519 signatures, authenticated encryption, hashes,
and keyed message authentication.

## Typical consumers

- PowerDNS optional libsodium-backed signer and cookie support
- packages needing compact modern crypto primitives without OpenSSL-heavy APIs

## Notes

This package installs the shared runtime on target and keeps headers plus
`pkg-config` metadata in staging for cross-build consumers.