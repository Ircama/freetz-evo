# Domoticz plugin: AWTRIX 3
  - Homepage: [https://github.com/galadril/Domoticz-AWTRIX3-Plugin](https://github.com/galadril/Domoticz-AWTRIX3-Plugin)
  - Changelog: [https://github.com/galadril/Domoticz-AWTRIX3-Plugin/commits](https://github.com/galadril/Domoticz-AWTRIX3-Plugin/commits)
  - Repository: [https://github.com/galadril/Domoticz-AWTRIX3-Plugin](https://github.com/galadril/Domoticz-AWTRIX3-Plugin)
  - Package: [master/make/pkgs/domoticz-awtrix3/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-awtrix3/)
  - Steward: Ircama


`domoticz-awtrix3` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*AWTRIX 3* plugin into the plugin directory of the hub.

Purpose: notifications and data on an AWTRIX 3 clock or LED matrix (it uses requests for the HTTP API of AWTRIX 3 and installs the icons it sends to the matrix).

## Setup

Setup -> Hardware -> AWTRIX3, enter the address of the device.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-AWTRIX3-Plugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The resource directories `icons`, `images` of the repository are installed too.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
