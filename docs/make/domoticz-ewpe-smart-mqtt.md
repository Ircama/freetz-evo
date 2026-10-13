# Domoticz plugin: EWPE Smart air conditioners (MQTT)
  - Homepage: [https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin](https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin)
  - Changelog: [https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin/commits](https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin/commits)
  - Repository: [https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin](https://github.com/stas-demydiuk/domoticz-ewpe-smart-mqtt-plugin)
  - Package: [master/make/pkgs/domoticz-ewpe-smart-mqtt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-ewpe-smart-mqtt/)
  - Steward: Ircama


`domoticz-ewpe-smart-mqtt` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*EWPE Smart air conditioners (MQTT)* plugin into the plugin directory of the hub.

Purpose: control of the EWPE Smart/Gree air conditioners over MQTT, with encrypted commands (it encrypts the commands with pycryptodome and ships its own MQTT client).

## Setup

Setup -> Hardware -> EWPE Smart MQTT, enter the MQTT broker and the device.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/ewpe-smart-mqtt` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  4 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-pycryptodome` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
