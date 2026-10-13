# Domoticz plugin: Xiaomi air purifiers
  - Homepage: [https://github.com/kofec/domoticz-AirPurifier](https://github.com/kofec/domoticz-AirPurifier)
  - Changelog: [https://github.com/kofec/domoticz-AirPurifier/commits](https://github.com/kofec/domoticz-AirPurifier/commits)
  - Repository: [https://github.com/kofec/domoticz-AirPurifier](https://github.com/kofec/domoticz-AirPurifier)
  - Package: [master/make/pkgs/domoticz-airpurifier/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-airpurifier/)
  - Steward: Ircama

`domoticz-airpurifier` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Xiaomi air purifiers* plugin into the plugin directory of the hub.

Purpose: control of the Xiaomi / Mi air purifiers that answer the miIO protocol
(AirPurifier 2 and the related models) over the LAN.

## Setup

Setup -> Hardware -> AirPurifier, enter the address of the purifier in Address and its
token in Mode1. The token is specific to the device and is read out once with a
`miiocli`-based tool or out of the Xiaomi Home app; the plugin then speaks to the
device directly on the LAN, so no Xiaomi account is involved at run time.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-AirPurifier` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  `plugin.py`, the `MyAir.py` helper and the upstream README (the repository has no other
  files). The whole tree moves to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-miio` in addition to the Domoticz module and the Python
  standard library: the package selects and depends on it, and the eleven modules
  `python-miio` pulls in are part of this tree too (`python3-miio`, `python3-micloud`,
  `python3-android-backup`, `python3-appdirs`, `python3-click`, `python3-construct`,
  `python3-croniter`, `python3-defusedxml`, `python3-netifaces`, `python3-pytz`,
  `python3-tqdm`);
* `plugin.py` runs `MyAir.py` as a separate process for every request and passes the
  token in the `MIIO_TOKEN` environment variable, so only that helper imports `miio`;
* upstream ships no license file: the README is installed with the plugin;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs a real purifier with
  a known token, which was not available here.

