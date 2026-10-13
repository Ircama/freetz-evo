# Domoticz plugin: Tasmota H801
  - Homepage: [https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin](https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin)
  - Changelog: [https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin/commits](https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin/commits)
  - Repository: [https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin](https://github.com/stas-demydiuk/domoticz-h801-tasmota-plugin)
  - Package: [master/make/pkgs/domoticz-tasmota-h801/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-tasmota-h801/)
  - Steward: Ircama


`domoticz-tasmota-h801` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Tasmota H801* plugin into the plugin directory of the hub.

Purpose: control of the H801 LED controllers (and of the Tasmota devices with PWM channels) from Domoticz (it ships its own MQTT client and the device controllers).

## Setup

Setup -> Hardware -> Tasmota H801, enter the MQTT broker.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/h801-tasmota-plugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  3 Python modules, the upstream documentation.
  The resource directories `controllers` of the repository are installed too.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so no additional Python package is required;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
