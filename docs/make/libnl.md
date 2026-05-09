# libnl 3.11.0 (netlink userspace library stack)
  - Homepage: [https://github.com/thom311/libnl](https://github.com/thom311/libnl)
  - Core API docs: [https://www.infradead.org/~tgr/libnl/doc/core.html](https://www.infradead.org/~tgr/libnl/doc/core.html)
  - Changelog: [https://github.com/thom311/libnl/releases](https://github.com/thom311/libnl/releases)
  - Repository: [https://github.com/thom311/libnl](https://github.com/thom311/libnl)
  - Package: [../../make/libs/libnl/](../../make/libs/libnl/)
  - Steward: Ircama

`libnl` provides the userspace APIs for Linux netlink families and route handling.
In Freetz-EVO it is packaged as a reusable shared-library stack for consumers such as `wavemon`.

## Runtime libraries

- `/usr/lib/libnl-3.so.200.26.0`
- `/usr/lib/libnl-cli-3.so.200.26.0`
- `/usr/lib/libnl-genl-3.so.200.26.0`
- `/usr/lib/libnl-nf-3.so.200.26.0`
- `/usr/lib/libnl-route-3.so.200.26.0`

## Build notes

- Source: upstream release tarball `libnl-3.11.0.tar.gz`
- Shared and static libraries are both built for staging.
- CLI helper binaries are not installed on target; only the shared libraries are packaged.
- The library can be externalized from `make menuconfig`.

## Typical consumers

- `wavemon`
- other packages using route, generic-netlink, or nft/netfilter netlink APIs