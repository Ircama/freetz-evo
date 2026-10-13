# Domoticz plugin: presence detection from an OpenWrt router (owrtwifi2domo)
  - Homepage: [https://github.com/enesbcs/owrtwifi2domo](https://github.com/enesbcs/owrtwifi2domo)
  - Changelog: [https://github.com/enesbcs/owrtwifi2domo/commits](https://github.com/enesbcs/owrtwifi2domo/commits)
  - Repository: [https://github.com/enesbcs/owrtwifi2domo](https://github.com/enesbcs/owrtwifi2domo)
  - Package: [master/make/pkgs/domoticz-owrtwifi2domo/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-owrtwifi2domo/)
  - Steward: Ircama


`domoticz-owrtwifi2domo` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*presence detection from an OpenWrt router (owrtwifi2domo)* plugin into the plugin directory of the hub.

Purpose: presence detection driven by the WiFi clients associated to an OpenWrt router (it ships its own MQTT client and needs no additional Python module).

## Setup

Setup -> Hardware -> owrtwifi2domo, enter the address and the credentials of the OpenWrt router.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/owrtwifi2domo` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so no additional Python package is required;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
