# tuyapp (local Tuya API client tools)
  - Homepage: [https://github.com/gordonb3/tuyapp](https://github.com/gordonb3/tuyapp)
  - Changelog: [https://github.com/gordonb3/tuyapp/commits/master](https://github.com/gordonb3/tuyapp/commits/master)
  - Repository: [https://github.com/gordonb3/tuyapp](https://github.com/gordonb3/tuyapp)
  - Package: [master/make/pkgs/tuyapp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/tuyapp/)
  - Steward: -

  - Depends on: jsoncpp, OpenSSL (libcrypto, libssl)
  - Provides: /usr/bin/tuya_switch, /usr/bin/tuya_status,
    /usr/bin/tuya_kwh_meter, /usr/bin/tuya_multi_kwh_meter,
    /usr/bin/tuya_monitor_and_control

tuyapp is a small C++ client library for the **Local Tuya API**, packaged
together with the upstream example clients. It was written as a lightweight
replacement for the Python based `tinytuya` project, specifically targeting
embedded machines.

Everything happens on the local network: the clients talk to the Tuya devices
directly over TCP (port 6668) and never contact the Tuya cloud.

## What is included

The upstream tree builds a static library (`libtuyapp.a`) plus one executable
per example. This package installs the clients that upstream's `make examples`
builds:

| Binary | Purpose |
|---|---|
| `tuya_switch` | Read the state of a device, or switch it `on` / `off` / `toggle` (optionally with a countdown) |
| `tuya_status` | Dump all data points (DPS) reported by a device |
| `tuya_kwh_meter` | Poll a single energy meter |
| `tuya_multi_kwh_meter` | Poll several energy meters in one go |
| `tuya_monitor_and_control` | Combined monitor + control client |

Protocol versions **3.3**, **3.4** and **3.5** are supported (3.1 is disabled,
matching upstream's default). The OpenSSL crypto backend is used.

A documented sample device database is installed at:

```
/usr/share/tuyapp/tuya-devices.json.sample
```

## Device credentials

All clients read their credentials from a file called `tuya-devices.json` in
the **current working directory** (so copy the sample there and edit it):

```
{
    "devices":[
        {"address":"192.168.10.91",
         "id":"123456789abcdef12345",
         "key":"abcdef1234567890",
         "name":"tuya1",
         "version":"3.3"
        },
        {"address":"192.168.10.92",
         "id":"123456789abcdef23456",
         "key":"abcdef1234567890",
         "name":"tuya2",
         "version":"3.4"
        }
    ]
}
```

- `address` — LAN IP address of the device
- `id` — the 20 character device id ("device_id" / `gwId`)
- `key` — the local key ("local_key")
- `name` — a friendly label used on the command line (case insensitive)
- `version` — protocol version: `3.3`, `3.4` or `3.5`

The local key can only be extracted while the device is still paired with the
Tuya/Smart Life app (e.g. with `tinytuya wizard` or one of the many online
helpers). Tuya devices generated with newer firmware may use local keys that
contain characters which need escaping when passed on the command line; this
is why the clients that read `tuya-devices.json` are the recommended ones.

## Usage examples

Read the current state of `tuya1` and its data points:

```
cd /tmp
cp /usr/share/tuyapp/tuya-devices.json.sample ./tuya-devices.json
tuya_status tuya1
tuya_switch tuya1
```

Switch `tuya1` on, off or toggle it:

```
tuya_switch tuya1 on
tuya_switch tuya1 off
tuya_switch tuya1 toggle
```

Switch on with a 30 minute countdown:

```
tuya_switch tuya1 on 30
```

Poll one or several energy meters:

```
tuya_kwh_meter tuya2
tuya_multi_kwh_meter tuya1 tuya2 tuya3
```

Monitor and control a device interactively:

```
tuya_monitor_and_control tuya2
```

## Notes

- The `tuya-devices.json` file is read from the current directory, so either
  `cd` into the directory holding it before running the clients, or call them
  from a wrapper script that does so.
- Only the TCP based local protocol is implemented; devices that exclusively
  use 868/433 MHz or cloud-only protocols are not supported.
- The `tuya_monitor_and_control` client runs until interrupted (Ctrl-C).

Project homepage: <https://github.com/gordonb3/tuyapp>
