# Domoticz plugin: Plugins Manager
  - Homepage: [https://github.com/stas-demydiuk/domoticz-plugins-manager](https://github.com/stas-demydiuk/domoticz-plugins-manager)
  - Changelog: [https://github.com/stas-demydiuk/domoticz-plugins-manager/commits](https://github.com/stas-demydiuk/domoticz-plugins-manager/commits)
  - Repository: [https://github.com/stas-demydiuk/domoticz-plugins-manager](https://github.com/stas-demydiuk/domoticz-plugins-manager)
  - Package: [master/make/pkgs/domoticz-plugins-manager/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-plugins-manager/)
  - Steward: Ircama


`domoticz-plugins-manager` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Plugins Manager* plugin into the plugin directory of the hub.

Purpose: install, update and remove the Python plugins of Domoticz from the web interface, using the upstream plugin index (it downloads the plugins from the upstream Plugins Manager index and installs them into the plugins folder of Domoticz).

## Setup

Setup -> Hardware -> Plugins Manager; the Plugins page of the Custom menu shows the catalogue with the install, update and remove buttons.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/plugins-manager` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  3 Python modules, the upstream documentation.
  The resource directories `api`, `frontend` of the repository are installed too.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
