# freetz-matter 0.1 (FRITZ!Box as a Matter device)
  - Package: [master/make/pkgs/freetz-matter/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/freetz-matter/)
  - Steward: Ircama
  - Provides: `/usr/bin/freetz-matter`, init script `rc.freetz-matter`
  - Configuration: `/mod/etc/default.freetz-matter/freetz-matter.cfg`
  - Matter stack: [`project-chip/rs-matter`](https://github.com/project-chip/rs-matter) 0.4.1, pinned to revision `4d4fd3a`
  - Endpoints: Temperature Sensor (0x0302), Smart Speaker (0x0022), root BasicInformation
  - Status: **implementation complete, cross-compilation of the stack verified up to the IDL codegen compile** — see [Build status](#build-status)

`freetz-matter` makes the FRITZ!Box itself a **Matter device**: a Matter controller (Apple Home, Google Home, Alexa, Home Assistant, or `python-matter-server` on a glibc host) commissions the box and can read its sensors and control its audio path. This is the opposite direction of [`matter-bridge`](matter-bridge.md): there the box *consumes* Matter devices, here the box *is* one.

**The two packages are independent**: neither requires the other, at build time or at run time. `freetz-matter` depends only on `alsa-utils` (for `amixer`) plus the Rust host toolchain — its Kconfig additionally requires uClibc ≥ 1.0.58 and IPv6 support, but no Freetz package — while `matter-bridge` is not selected, not depended on, and not referenced by its init script or configuration. They can be installed together without conflict, because they do not share ports or files: `matter-bridge` is a WebSocket server on TCP 5580, `freetz-matter` is a Matter node on UDP 5540 (the standard Matter port).

For a fully local Domoticz setup, the native [matter-bridge](matter-bridge.md) daemon can automatically commission this accessory at `[::1]:5540`, subscribe to its attributes and control its speaker. Domoticz connects to `127.0.0.1:5580`; no external controller is needed for this local chain. Other controllers remain alternatives, not requirements.

No Node.js and no hub software runs on the box: the Matter stack is pure Rust ([`rs-matter`](https://github.com/project-chip/rs-matter)), compiled natively for MIPS/uClibc.

## Why rs-matter

| Candidate | Verdict |
|---|---|
| `connectedhomeip` (CHIP SDK) | 79 submodules, GN + Ninja + glibc/avahi/dbus — not portable to uClibc/MIPS |
| `python-matter-server` / `matterjs-server` | embed the CHIP SDK — same problem (they run on a host, which is what `matter-bridge` is for) |
| `rs-matter` | pure Rust, `no_std`-capable, `os` feature for Linux (`async-io`, `if-addrs`), examples for `onoff_light`, `dimmable_light`, `speaker`, `thermostat`, `bridge` — **chosen** |

## Endpoints

| EP | Device type | Clusters | Backed by |
|---|---|---|---|
| 0 | Root Node | `BasicInformation` | real box data: `vendor_name`, `product_name` (model), `sw_ver_str` (FRITZ!OS version), `hw_ver_str` (AVM revision), `serial_no` (LAN MAC), `manufacturing_date` |
| 1 | Temperature Sensor `0x0302` | `TemperatureMeasurement` `0x0402` | the same sensor chain as [`box_info`](box_info.md): `/proc/chip_temperature` → `/sys/devices/virtual/thermal/thermal_zone0/temp` → `/proc/avm/powermanagmentressourceinfo/powerdevice_temperature` → `/proc/avm/temp_sensors`, in that priority order |
| 2 | Smart Speaker `0x0022` | `OnOff` `0x0006`, `LevelControl` `0x0008` | ALSA through `amixer` (from `alsa-utils`): `On`/`Off` = unmute/mute of the PCM/Master control, `MoveToLevel*` = volume 1..254 mapped to 0..100 % |

`measured_value` reports in 1/100 °C (Matter unit) and bumps the data version only when the reading really changed, so subscriptions behave. `min_measured_value`/`max_measured_value` are -40 °C/+125 °C and `tolerance` is 0.5 °C.

### Further controls that fit the same pattern

Everything below is a small handler over an existing Freetz data source and can be added without new dependencies:

| Idea | Cluster | Source |
|---|---|---|
| WLAN/LAN client present | `OccupancySensing` `0x0406` | `/proc/net/arp`, `wlan` client counters |
| Internet/WAN up | `BooleanState` `0x0045` | `box_info` connection state |
| DECT/guest WLAN/telephony on-off | `OnOff` / `GenericSwitch` | AVM `ctlmgr` states, `box_info` |
| Firmware update available | `BooleanState` | `/etc/version` vs. the OSP page |
| USB storage usage | `%`-ish attribute | `df`/`mounted` pages |
| 433 MHz sensors (see the SDR packages) | `TemperatureMeasurement`, `OccupancySensing` | `rtl_433` JSON output |
| Audio playback state / track | `MediaPlayback` `0x0506` | `mpd`/`mpc`, `shairport-sync` |

## Configuration
modconf set `/mod/etc/default.freetz-matter/freetz-matter.cfg` (all values editable in the web UI, saved in `/mod/etc/conf/freetz-matter.cfg`):

| Variable | Default | Meaning |
|---|---|---|
| `FREETZ_MATTER_ENABLED` | `no` | autostart on boot |
| `FREETZ_MATTER_PORT` | `5540` | Matter UDP port (the standard one) |
| `FREETZ_MATTER_STORE` | `/tmp/flash/freetz-matter` | fabric store: commissioned fabrics, ACLs, subscriptions; run modsave after commissioning |
| `FREETZ_MATTER_VERBOSE` | `no` | debug logging |
| `FREETZ_MATTER_CONFIG_WAIT` | `120` | seconds to wait for `/usr/bin/freetz-matter` when the binary lives on external storage; the wait runs in a background subshell, `0` disables it |
| `FREETZ_MATTER_EXTRA_ARGS` | *(empty)* | extra daemon options |

`pkg_pre_save` validates the port and the store path, warns when the store is not on persistent storage and when `amixer` is missing; nothing is restarted implicitly.

### Externalization

`freetz-matter` can be moved to external storage from the **External** menu (`EXTERNAL_FREETZ_PACKAGE_FREETZ_MATTER`): `/usr/bin/freetz-matter` is the entire payload (4.5 MB stripped) and is the only declared file. The init script, the Freetz configuration and the fabric store remain in the firmware — they are a few kilobytes, needed at boot, and `/mod/etc` is where the store has to live anyway to survive reboots. Because the rs-matter stack is linked in statically, the binary has no companion files to carry along, and everything it opens is addressed by absolute paths.

### mDNS / DNS-SD

The daemon advertises the device with rs-matter's built-in mDNS responder:
`_matterc._udp` while it is uncommissioned, `_matter._tcp` — with the
`_I<compressed-fabric-id>._sub._matter._tcp` subtypes controllers look for — and
the A/AAAA records of `freetz-matter.local` once it holds a fabric. A controller
on the LAN therefore finds the box without knowing its address.

FRITZ!OS has its own closed mDNS responder (`libavmdnsdomains.so`,
`libavmdnsnotify.so`, used by `ctlmgr`, `multid`, `upnpd`, ...) which already
holds UDP 5353 for `fritz.box` and the AVM services. The socket of
`freetz-matter` is opened with `SO_REUSEADDR` and binds `[::]:5353` next to it:
each responder answers only for its own records, so `fritz.box` keeps working
(verified on a FRITZ!Box 7590AX: both the AVM `_http._tcp` record and the Matter
`_matter._tcp` records answer the same query). The LAN interface is selected
automatically — `lan` on a FRITZ!Box, a bridge elsewhere, `MATTER_MDNS_INTERFACE`
to override it — the IPv4 address is optional, and a missing or busy mDNS socket
only disables the advertisement, never the local chain.

## Usage

```sh
# start it once and read the commissioning codes from the log
/etc/init.d/rc.freetz-matter start
tail -f /tmp/rc.freetz-matter.log     # QR code + manual pairing code

# or through the web UI: Status -> Logs -> rc.freetz-matter
```

Because the device starts uncommissioned, `freetz-matter` prints the standard QR code and the manual pairing code on stdout on the first start; the init script redirects them into the service log. After commissioning, the fabrics live in `FREETZ_MATTER_STORE` and the codes are not printed again.

Test the device from any Matter host with:

```sh
matter-server --storage-path /tmp/ms --port 5580          # python-matter-server
# then commission with the printed manual code and read the temperature:
#   matter_server.client -> commission_with_code(...) / read_attribute(1, "1/1026/0")
```

The `matter-bridge` package's `tests/conformance-python-matter-server.py` shows how to drive the same JSON API in a script.

## How it is built

`freetz-matter` is a Rust package following the pattern of `ripgrep`/`broot`: nightly Cargo with `-Z build-std=std,panic_abort` for the tier-3 target `mips-unknown-linux-uclibc`, the Freetz cross linker/archiver, and `-C link-arg=-Wl,-no-pie` (PIE binaries segfault with `ld-uClibc.so.1` on MIPS). The application sources live in the package directory (`src/`, `Cargo.toml`) and are copied into the Freetz source directory before the build; `rs-matter` itself is fetched by cargo from its git repository, pinned by revision.

Three fixes were needed to make this dependency graph build for uClibc/MIPS; the first two are now shared macros in `make/include/650-rust-cargo.mk`:

1. **`rustix` with the libc backend and without `linux_raw_dep`** (what rs-matter pulls): `linux_raw_sys` is not linked in that configuration, so the missing uClibc items cannot be declared in rustix's private `c` module and are substituted at their use sites instead — `preadv`/`pwritev` (no `*64` aliases in uClibc), `STATX__RESERVED`, `__fsword_t`, `EHWPOISON`, `AF_XDP`, `CMSPAR`, `CRDLY`, `FFDLY`, `VTDLY`. New macro: `RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT`.
2. **`getrandom`**: uClibc's `libc` crate has no `getrandom()`, so the `SYS_getrandom` syscall fallback is applied (existing macro `GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT`).
3. **Build profile**: `rs-matter`'s `build.rs` generates ~30 MB of cluster code from the Matter IDL. With the upstream profile (fat LTO + `codegen-units=1`) a single `rustc` job needs several GB and is **killed with SIGKILL** on a 4-core/8 GB build host. The package therefore uses its own profile (`opt-level = "s"`, `lto = false`, `codegen-units = 16`, `strip = true`), which is also what keeps the binary small enough for the box.

## Build status

| Step | Result |
|---|---|
| `rs-matter` 0.4.1 cross-compiled for `mips-unknown-linux-uclibc` (nightly, `-Z build-std`, Freetz cross linker, `-no-pie`) | **yes** — `librs_matter` is produced for the target (~294 MB rlib) once the two patches above are applied; the whole crates.io dependency graph (`rustix` 1.1.5, `getrandom` 0.4.3, `nix` 0.31.3, `socket2`, `async-io`, `if-addrs`, `embassy-*`, the `rustcrypto` stack) builds with it |
| `freetz-matter` application crate | **yes** — clean build, no warnings; the binary is **8.5 MB** before stripping, `ELF 32-bit MSB executable, MIPS, MIPS32 rel2` |
| `make freetz-matter-precompiled` (full freetz package build, 0 errors) | **yes** — installs `/usr/bin/freetz-matter` (**4.5 MB** after `INSTALL_BINARY_STRIP`), `/etc/init.d/rc.freetz-matter` (0755) and `/etc/default.freetz-matter/{freetz-matter.cfg,freetz-matter.save}` into the package root |
| Runtime dependencies | only `libc.so.0`, `ld-uClibc.so.1` and `libgcc_s.so.1` (interpreter `/lib/ld-uClibc.so.0`), i.e. all present in the FRITZ!Box image — the Rust runtime is linked in statically |
| End-to-end test on a box | not done: needs a Matter controller to commission the device |

### Build-host memory

`rs-matter`'s `build.rs` generates ~30 MB of Rust from the Matter IDL, and the generated crate is the memory bottleneck: a single `rustc` job peaks at **~5.6 GB RSS**. On the 8 GB build host used here the job was killed with `SIGKILL` while swap was a full 2 GB partition; after the swap grew to 10 GB the same compile completed with no change to the sources. The package therefore builds with a deliberately serialized setup — `CARGO_BUILD_JOBS=1`, `-Zthreads=1` and a memory-friendly profile (`opt-level = 1`, `lto = false`, `codegen-units = 256`) in `Cargo.toml`. On a host with ≥16 GB RAM the stock profile also fits; a trimmed cluster set (see below) would remove the constraint altogether.

Nothing of this needs Node.js, and no CHIP SDK build is involved.

## See also

- [HOME-AUTOMATION.md](../HOME-AUTOMATION.md) — the whole home automation subsystem of Freetz-EVO
- [MATTER.md](../MATTER.md) — Matter on the box: directions, stacks and limitations
- [matter-bridge.md](matter-bridge.md) — the opposite direction: Domoticz as a Matter controller, no Node.js
- [ot-br-posix.md](ot-br-posix.md) — Thread border router, for Thread-based Matter devices
- [box_info.md](box_info.md) — the page whose data the temperature endpoint reproduces
