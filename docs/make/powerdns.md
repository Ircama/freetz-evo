# PowerDNS Authoritative Server 5.0.5
  - Homepage: [https://www.powerdns.com/](https://www.powerdns.com/)
  - Manpage: [https://doc.powerdns.com/authoritative/](https://doc.powerdns.com/authoritative/)
  - Changelog: [https://doc.powerdns.com/authoritative/changelog/](https://doc.powerdns.com/authoritative/changelog/)
  - Repository: [https://github.com/PowerDNS/pdns](https://github.com/PowerDNS/pdns)
  - Package: [master/make/pkgs/powerdns/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/powerdns/)
  - Steward: -

PowerDNS in this port packages the Authoritative Server only. Upstream `recursor`
and `dnsdist` are separate products and are not included here.

### Overview

This freetz port follows a minimal default profile: no backend and no optional
server feature is enabled unless selected explicitly in `menuconfig`.

The runtime integration installs:

- `pdns_server`
- optional helpers such as `pdnsutil`, `pdns_control`, `zone2sql`, `zone2json`
- optional diagnostic tools (`sdig`, `pdns_notify`, `dnsbulktest`, and the rest of the upstream tools set)
- freetz init/default files under `/mod/etc/default.powerdns/` and `/etc/init.d/rc.powerdns`

At first start, the init script copies the sample configuration to:

```text
/tmp/flash/powerdns/pdns.conf
```

The sample keeps PowerDNS on `127.0.0.1:5300`, with API and webserver disabled.

### Backends

The current port supports these Authoritative Server backends, each selectable as
static or dynamic where upstream supports it:

- `bind`
- `pipe`
- `godbc`
- `gmysql`
- `gpgsql`
- `gsqlite3`
- `geoip`
- `lmdb`
- `lua2`
- `remote`
- `tinydns`

Backends not currently wired into this freetz tree because target-side
dependencies are missing:

- `ldap`

The `ldap` backend is still blocked specifically by missing Kerberos headers and
libraries (`krb5`, `krb5-gssapi`) required by upstream PowerDNS in addition to
OpenLDAP itself.

Remember to configure at least one `launch=` backend in
`/tmp/flash/powerdns/pdns.conf`, otherwise the daemon will refuse to start.

### Optional Features

The package currently exposes these optional upstream Authoritative Server
features:

- Lua records
- DNS-over-TLS via either OpenSSL or the alternative GnuTLS provider
- `ixfrdist` as an optional standalone binary
- libsodium-backed signer and cookie support
- IPCipher
- ZeroMQ connector for the `remote` backend
- verbose logging
- externalization for the server, helper tools, `ixfrdist`, and dynamic modules

Upstream features intentionally left unavailable in this tree because the needed
packages are missing or the integration is not validated yet:

- PKCS#11 support
- GSS-TSIG support

PKCS#11 support needs `p11-kit-1`, and GSS-TSIG support needs Kerberos/GSS
libraries (`krb5`, `krb5-gssapi`), neither of which is currently packaged in
this tree.

### Toolchain Requirement

PowerDNS 5.x requires a modern C++17-capable toolchain. In practice this means
`FREETZ_TARGET_GCC_8_MIN=y` for this port.

On legacy targets such as `mipsel_gcc-4.6.4_uClibc-0.9.32.1`, `menuconfig` shows
only an explanatory comment and the package cannot be built.

### Notes

If you want PowerDNS to listen on port `53`, disable AVM DNS/LLMNR through the
package option provided in `menuconfig` and adapt `pdns.conf` accordingly.

During cross-builds, upstream tries to generate `pdns.conf-dist` by running the
freshly built `pdns_server`. On freetz this target binary is not runnable on the
build host, so the package intentionally installs a small fallback
`pdns.conf-dist` placeholder instead. This is expected and does not affect the
normal runtime path, because freetz uses `/mod/etc/default.powerdns/pdns.conf`
as the runtime template copied on first start.

The default sample does not enable the API or webserver. Turn them on manually
only after you have configured the backend and access control settings you need.