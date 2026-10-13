# Domoticz plugin: WLANThermo
  - Homepage: [https://github.com/galadril/Domoticz-WLANThermo-Plugin](https://github.com/galadril/Domoticz-WLANThermo-Plugin)
  - Changelog: [https://github.com/galadril/Domoticz-WLANThermo-Plugin/commits](https://github.com/galadril/Domoticz-WLANThermo-Plugin/commits)
  - Repository: [https://github.com/galadril/Domoticz-WLANThermo-Plugin](https://github.com/galadril/Domoticz-WLANThermo-Plugin)
  - Package: [master/make/pkgs/domoticz-wlan-thermo/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-wlan-thermo/)
  - Steward: Ircama


`domoticz-wlan-thermo` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*WLANThermo* plugin into the plugin directory of the hub.

Purpose: temperature readings of the WLANThermo probes (grills and barbecues) (it uses requests for the HTTP API of WLANThermo).

## Setup

Setup -> Hardware -> WLANThermo, enter the address of the device.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-WLANThermo-Plugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
