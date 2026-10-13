# Domoticz plugin: Zigbee2MQTT
  - Homepage: [https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin](https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin)
  - Changelog: [https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin/commits](https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin/commits)
  - Repository: [https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin](https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin)
  - Package: [master/make/pkgs/domoticz-zigbee2mqtt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-zigbee2mqtt/)
  - Steward: Ircama


`domoticz-zigbee2mqtt` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Zigbee2MQTT* plugin into the plugin directory of the hub.

Purpose: expose the Zigbee devices managed by Zigbee2MQTT in Domoticz, with adapters for hundreds of models and a configuration frontend (it ships its own model adapters and talks to Zigbee2MQTT through an MQTT broker).

## Setup

Setup -> Hardware -> Zigbee2MQTT, enter the address and port of the MQTT broker used by Zigbee2MQTT.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/zigbee2mqtt` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  11 Python modules, the upstream documentation.
  The resource directories `adapters`, `api`, `devices`, `features`, `frontend` of the repository are installed too.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
