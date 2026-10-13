# Domoticz plugin: Milight ESP8266 hub
  - Homepage: [https://github.com/etsach/espmilighthub-domoticz](https://github.com/etsach/espmilighthub-domoticz)
  - Changelog: [https://github.com/etsach/espmilighthub-domoticz/commits](https://github.com/etsach/espmilighthub-domoticz/commits)
  - Repository: [https://github.com/etsach/espmilighthub-domoticz](https://github.com/etsach/espmilighthub-domoticz)
  - Package: [master/make/pkgs/domoticz-milight-esp8266/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-milight-esp8266/)
  - Steward: Ircama


`domoticz-milight-esp8266` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Milight ESP8266 hub* plugin into the plugin directory of the hub.

Purpose: control of the groups and lamps driven by the ESP8266 gateway for Milight/AppLamp, over MQTT (it speaks to the ESP8266 gateway with its own MQTT client, so the native RF driver of Domoticz is not involved).

## Setup

Setup -> Hardware -> espmilighthub, enter the address of the ESP8266 gateway.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/espmilighthub-domoticz` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so no additional Python package is required;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
