# tuya-iot-core-sdk (Tuya IoT Core SDK for C)
  - Homepage: [https://github.com/tuya/tuya-iot-core-sdk](https://github.com/tuya/tuya-iot-core-sdk)
  - Changelog: [https://github.com/tuya/tuya-iot-core-sdk/commits/main](https://github.com/tuya/tuya-iot-core-sdk/commits/main)
  - Repository: [https://github.com/tuya/tuya-iot-core-sdk](https://github.com/tuya/tuya-iot-core-sdk)
  - Package: [master/make/pkgs/tuya-iot-core-sdk/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/tuya-iot-core-sdk/)
  - Steward: Ircama

  - Depends on: cmake (host), patchelf (host, when a separate AVM uClibc is used)
  - Provides: /usr/bin/custom_protocol_basic_demo, /usr/bin/data_model_basic_demo,
    /usr/bin/ota_basic_demo, /usr/bin/subdevice_basic_demo

The Tuya IoT Core SDK for C is the official client library for the **Tuya
Cloud**: it connects a device over MQTT with TLS (mbedTLS) and implements the
Tuya data model, OTA updates, sub-device handling and custom protocols. Unlike
the `tuyapp` package, which speaks the *local* Tuya LAN
protocol, this SDK talks to the Tuya cloud endpoints.

## What is included

Upstream ships no `install()` rules and only builds example programs, so this
package installs the four demos as stand-alone binaries:

| Binary | Demonstrates |
|---|---|
| `custom_protocol_basic_demo` | raw custom protocol messages |
| `data_model_basic_demo` | DP (data point) reporting and receiving |
| `ota_basic_demo` | OTA firmware update flow |
| `subdevice_basic_demo` | gateway handling of sub-devices |

The SDK itself, mbedTLS 2.16.8, coreMQTT, coreJSON and coreHTTP are vendored by
upstream into the source archive and are linked statically into each binary, so
no additional freetz library is required. The demos embed the Tuya CA
certificate (`tuya_cacert.h`), therefore no `ca-certificates` package is
needed either. Because of the bundled TLS stack each binary is fairly large
(~270-340 kB).

## Runtime credentials

Upstream hardcodes placeholder credentials in the demo sources. The freetz
patch `patches/100-demo-credentials-from-env.patch` keeps the placeholders as
fallbacks but lets them be overridden at runtime through the environment:

| Variable | Meaning |
|---|---|
| `TUYA_PRODUCT_ID` | product (PID) the device is registered with |
| `TUYA_DEVICE_ID` | device ID (UUID) |
| `TUYA_DEVICE_SECRET` | device secret used for MQTT authentication |
| `TUYA_MQTT_HOST` | cloud endpoint, default `m1.tuyacn.com` |

Data-centre endpoints are `m1.tuyacn.com` (China), `m1.tuyaus.com` (US),
`m1.tuyaeu.com` (Europe) and `m1.tuyain.com` (India).

```sh
export TUYA_PRODUCT_ID=...  TUYA_DEVICE_ID=...  TUYA_DEVICE_SECRET=...
export TUYA_MQTT_HOST=m1.tuyaeu.com
data_model_basic_demo
```

Keep the credentials out of the command line (they would be visible in `ps`):
put the exports in a file below `/mod/etc/` and source it, or start the demo
through a small wrapper script.

## Notes

- Upstream has no usable release (only an ancient `0.0.1` tag), so the package
  is pinned to the `main` commit `0208badefb2003d30e70b5b875395e3187c850d9`.
- Upstream forbids in-source builds, so a dedicated `build/` directory is used
  and the binaries are taken from `build/bin/`.
- `cmake_minimum_required(VERSION 3.2.0)` is rejected by CMake 4.x, hence
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`; `BUILD_TESTS`, the submodule clone and
  the certificate download are switched off.
- Requires uClibc 1.0.58 or newer.
- The demos loop forever and reconnect, which makes them suitable for a
  long-running test but not for a simple one-shot script; run them in the
  background or under `timeout`.
- **TuyaOpen** (the MCU/AI-IoT framework of the same vendor) is *not*
  portable to freetz: it is a firmware framework targeting Tuya T2/T3/T5AI,
  ESP32, LN882H, BK7231X and GD32 boards, with per-platform source trees that
  are downloaded separately and a Kconfig/`tos.py`/`uv` build environment; it
  produces flashable MCU images and has no MIPS/uClibc target. Use this SDK
  (Tuya Cloud) or `tuyapp` (local Tuya API) instead.

