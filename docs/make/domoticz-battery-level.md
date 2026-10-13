# Domoticz plugin: BatteryLevel
  - Homepage: [https://github.com/999LV/BatteryLevel](https://github.com/999LV/BatteryLevel)
  - Changelog: [https://github.com/999LV/BatteryLevel/commits](https://github.com/999LV/BatteryLevel/commits)
  - Repository: [https://github.com/999LV/BatteryLevel](https://github.com/999LV/BatteryLevel)
  - Package: [master/make/pkgs/domoticz-battery-level/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-battery-level/)
  - Steward: Ircama


`domoticz-battery-level` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*BatteryLevel* plugin into the plugin directory of the hub.

Purpose: monitoring of the battery level of the devices, with notifications on the thresholds (it connects to the MQTT broker with paho-mqtt).

## Setup

Setup -> Hardware -> BatteryLevel, enter the MQTT broker and the devices to follow.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/BatteryLevel` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-paho-mqtt` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
