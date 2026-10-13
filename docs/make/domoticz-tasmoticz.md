# Domoticz plugin: Tasmoticz
  - Homepage: [https://github.com/joba-1/Tasmoticz](https://github.com/joba-1/Tasmoticz)
  - Changelog: [https://github.com/joba-1/Tasmoticz/commits](https://github.com/joba-1/Tasmoticz/commits)
  - Repository: [https://github.com/joba-1/Tasmoticz](https://github.com/joba-1/Tasmoticz)
  - Package: [master/make/pkgs/domoticz-tasmoticz/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-tasmoticz/)
  - Steward: Ircama


`domoticz-tasmoticz` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Tasmoticz* plugin into the plugin directory of the hub.

Purpose: expose the Tasmota devices of an MQTT broker in Domoticz, with automatic configuration and sync commands (it ships its own MQTT client and the Tasmota support).

## Setup

Setup -> Hardware -> Tasmoticz, enter the MQTT broker and the Tasmota topic prefix.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Tasmoticz` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  3 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
