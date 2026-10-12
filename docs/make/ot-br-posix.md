# OpenThread Border Router (ot-br-posix) 2026.10.0
  - Homepage: [https://github.com/openthread/ot-br-posix](https://github.com/openthread/ot-br-posix)
  - Changelog: [https://github.com/openthread/ot-br-posix/releases](https://github.com/openthread/ot-br-posix/releases)
  - Repository: [https://github.com/openthread/ot-br-posix](https://github.com/openthread/ot-br-posix)
  - Package: [master/make/pkgs/ot-br-posix/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ot-br-posix/)
  - Steward: Ircama

  - Provides: `/usr/sbin/otbr-agent`, `/usr/sbin/ot-ctl`, init script `rc.otbr`
  - Depends on: [openthread](openthread.md) (same version, source tree reused)
  - Configuration: `/mod/etc/default.otbr/otbr.cfg` (`OTBR_ENABLED`, `OTBR_INFRA_IF`, `OTBR_RADIO_URL`, …)
  - Status: **built and installed** — `otbr-agent` (2,474,112 bytes, stripped) and `ot-ctl` (8,356 bytes) are produced for `mips_gcc-13.4.0_uClibc-1.0.59-nptl_kernel-4.9` in a single 100%-clean run

`otbr-agent` is the OpenThread **Border Router** for Linux: it owns an 802.15.4 Radio Co-Processor (RCP), forms the Thread network, acts as the Thread Routing Manager and connects the mesh to the IPv6 home network, publishing the border router services with OpenThread's own mDNS/DNS-SD stack. This is the Thread side of a Matter installation: Matter-over-Thread devices become reachable from the LAN, which is what a Matter controller (and therefore the Domoticz Matter driver, which talks to `python-matter-server` over WebSocket) needs.

## Freetz integration

### Configuration

Defaults live in `/etc/default.otbr/otbr.cfg`, values saved from the web interface end up in `/mod/etc/conf/otbr.cfg`. All variables are exported so the Freetz configuration page shows them.

| Variable | Default | Meaning |
|---|---|---|
| `OTBR_ENABLED` | `no` | start `otbr-agent` at boot |
| `OTBR_INFRA_IF` | `br0` | infrastructure (backbone) interface, `br0` = LAN bridge, `wlan0` = 2.4 GHz WLAN |
| `OTBR_RADIO_URL` | `spinel+hdlc+uart:///dev/ttyACM0` | spinel URL of the RCP |
| `OTBR_LOG_LEVEL` | *(empty)* | value passed to `-d` (0 = most verbose … 7) |
| `OTBR_CONFIG_WAIT` | `120` | seconds to wait for the RCP device at boot (`0` = start immediately) |
| `OTBR_EXTRA_ARGS` | *(empty)* | extra `otbr-agent` options, e.g. `-v` or `-B eth0` |

`otbr.save` validates the values (numeric wait time, interface and spinel URL required when enabled) and warns when `/dev/net/tun` is missing. It never restarts the daemon: settings are applied on the next (re)start.

### Boot behaviour

`rc.otbr` uses the modlib helpers (`modlib_start`, `modlib_stop`, `modlib_restart`, `modlib_status`) and registers a daemon entry for the Freetz services page. Because the RCP is usually a USB dongle that enumerates late, the init script extracts the device path from `OTBR_RADIO_URL` and waits for it in a **background subshell** (which re-sources the configuration) — the boot sequence is never blocked. With `OTBR_CONFIG_WAIT=0` the agent starts immediately; with a non-`/dev/` URL (unix socket or TCP RCP) there is nothing to wait for.

### Runtime requirements on the Fritz!Box

- an 802.15.4 RCP (e.g. nRF52840 dongle) flashed with the OpenThread RCP firmware, on a USB/serial port
- `/dev/net/tun` — the agent creates the Thread interface `wpan0` with it
- IPv6 forwarding enabled (`net.ipv6.conf.all.forwarding=1`)
- `ip6tables`/`iptables` for the optional ingress firewall features (freetz ships iptables)

## Build notes

- All optional upstream components are **disabled**, which removes the protobuf, dbus, jsoncpp, cJSON, cpp-httplib and libsystemd dependencies completely:
  `OTBR_DBUS=OFF`, `OTBR_WEB=OFF`, `OTBR_REST=OFF` (these three are the only consumers of protobuf/jsoncpp/cJSON/cpp-httplib), `OTBR_NAT64=OFF`, `OTBR_DHCP6_PD=OFF`, `OTBR_BACKBONE_ROUTER=OFF`, `OTBR_NFTABLES=OFF`, `OTBR_PF=OFF`, `OTBR_FEATURE_FLAGS=OFF`, `OTBR_TELEMETRY_DATA_API=OFF`.
- `OTBR_MDNS=openthread` makes the OpenThread core publish mDNS/DNS-SD itself. This avoids the mDNSResponder/Bonjour port; Avahi is explicitly unsupported by upstream for this role.
- The OpenThread sources are **not vendored** here: upstream hardcodes the path with a plain `set(OPENTHREAD_PROJECT_DIRECTORY ${PROJECT_SOURCE_DIR}/third_party/openthread/repo)` that cannot be overridden on the command line, so the package symlinks `third_party/openthread/repo` to the source directory of the [openthread](openthread.md) package (which is built first and provides the matching version, including the pinned mbedTLS submodule). The other submodules of this repository (`third_party/cJSON`, `third_party/cpp-httplib`) belong to the REST component and are not needed.
- Same as OpenThread: `cmake_minimum_required(VERSION 3.10.2)` → `-DCMAKE_POLICY_VERSION_MINIMUM=3.10`, and `-DCMAKE_EXE_LINKER_FLAGS="-latomic"` on 32-bit targets.

## Not packaged from the Matter ecosystem

For completeness, the upstream projects that a Matter installation normally consists of were evaluated as well:

- **connectedhomeip** (Matter SDK): not portable in this build environment. The repository has **79 git submodules** (pigweed, OpenThread, ot-br-posix, mbedtls, nanopb, …), its build system is **GN + ninja** (GN is not part of Freetz and would have to be obtained as a host binary from pigweed/CIPD), and the Linux reference builds additionally expect glib, avahi/dbus and GObject introspection development packages. The Domoticz Matter driver does not link the SDK anyway: it speaks WebSocket to `python-matter-server`/`python-matterjs-server`, which in turn runs the SDK with Python bindings outside the Fritz!Box.
- **rs-matter**: a pure-Rust Matter implementation that covers **both roles**. It is packaged in this tree as [`freetz-matter`](freetz-matter.md) (FRITZ!Box as a Matter *device*: temperature sensor and smart speaker endpoints, real box data in `BasicInformation`), and its controller side (`onboard::Commissioner`, fabric PKI, PASE/CASE initiators, interaction-model client) is what the milestone 2 of [`matter-bridge`](matter-bridge.md) builds on. The tree's Rust cross support (`make/host-tools/rust-host`, `make/include/650-rust-cargo.mk`) is what makes both possible.

Note: the Domoticz Matter hardware driver is implemented in Domoticz itself (`hardware/Matter.cpp`, a WebSocket client for port 5580) and needs no extra package.

See [MATTER.md](../MATTER.md) for the complete Node-free Matter setup (controller on a glibc host with `python-matter-server`, Thread border router and Domoticz on the box), the JSON protocol the driver expects, and the current state of the native in-box controller ([matter-bridge](matter-bridge.md) milestone 2).
