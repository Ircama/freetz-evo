# OpenThread 2026.10.0
  - Homepage: [https://openthread.io/](https://openthread.io/)
  - Changelog: [https://github.com/openthread/openthread/releases](https://github.com/openthread/openthread/releases)
  - Repository: [https://github.com/openthread/openthread](https://github.com/openthread/openthread)
  - Package: [master/make/pkgs/openthread/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/openthread/)
  - Steward: Ircama

  - Provides: `/usr/bin/ot-daemon`, `/usr/bin/ot-ctl`
  - Requires: an external 802.15.4 Radio Co-Processor (RCP) for radio access
  - Related: [ot-br-posix](ot-br-posix.md) (Border Router, reuses this source tree)

OpenThread is Google's open source implementation of the **Thread** networking protocol (Thread 1.4.0: IPv6, 6LoWPAN, IEEE 802.15.4 MAC security, Mesh Link Establishment, mesh routing and Border Router support). Thread is the low power mesh network that carries Matter-over-Thread devices — the missing radio piece on the Fritz!Box side.

## What this package builds

The POSIX (Linux) platform is used, which produces the Thread daemon and its control client:

| Binary | Purpose |
|---|---|
| `/usr/bin/ot-daemon` | the Thread stack as a daemon (runs the device) |
| `/usr/bin/ot-ctl` | control client with the **full CLI command set**, talking to a running `ot-daemon` |

Upstream selects the POSIX application as **either/or**: `OT_APP_DAEMON` (used here) or `OT_APP_CLI` for a standalone interactive `ot-cli`. The daemon model was chosen because `ot-ctl` offers the same commands while the Thread stack keeps running in the background (a standalone CLI would exit with the session).

The 802.15.4 radio is **not** part of this package: an 802.15.4 SoC (typically an nRF52840 dongle) has to run the OpenThread RCP firmware and is reached through spinel, for example `spinel+hdlc+uart:///dev/ttyACM0`. The RCP firmware itself is built with the ARM toolchain of the dongle vendor, not with the Freetz toolchain.

## Build notes

- `third_party/mbedtls/repo` is the only git submodule of the `v2026.10.0` tag. GitHub source archives never contain submodule contents and OpenThread builds mbedTLS as a bundled static library with its own `mbedtls-config.h`, therefore the pinned mbedTLS commit (`e185d7fd85499c8ce5ca2a54f5cf8fe7dbe3f8df`) is downloaded as a second tarball and unpacked into place before configure runs. `third_party/tcplp` is vendored in the archive.
- Upstream uses `cmake_minimum_required(VERSION 3.10.2)`, so the tree's CMake 4 needs `-DCMAKE_POLICY_VERSION_MINIMUM=3.10`.
- POSIX targets are enabled with `-DOT_PLATFORM=posix -DOT_BUILD_EXECUTABLES=ON -DOT_DAEMON=ON`; the POSIX platform links only `libutil`, `librt` and `libpthread` (netlink is used through raw sockets, **no libnl dependency**).
- `-DCMAKE_EXE_LINKER_FLAGS="-latomic"` is required on 32-bit targets for 64-bit atomics (same workaround as ffmpeg, cmus and openssl).
- OpenThread 2026 needs a C++11 capable toolchain, so the package is limited to `FREETZ_TARGET_UCLIBC_1_0_58_MIN` (GCC 13.4 in this tree).

## Usage

```bash
# start a Thread node with an RCP attached to /dev/ttyACM0
ot-daemon 'spinel+hdlc+uart:///dev/ttyACM0' &

# inspect/control the node (full CLI command set)
ot-ctl state
ot-ctl dataset active
ot-ctl ipaddr
```

For a full Border Router (Routing Manager, mDNS/DNS-SD advertisement of the Thread network, NAT64 optional) install the [ot-br-posix](ot-br-posix.md) package, which ships `otbr-agent` and reuses this package's source tree.

See [MATTER.md](../MATTER.md) for how Matter devices reach Domoticz without Node.js, and which part of the chain belongs on the box.
