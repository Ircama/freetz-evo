# Domoticz plugin: GoodWe solar inverter (SEMS API)
  - Homepage: [https://github.com/JanJaapKo/domoticz-GoodWeSEMS](https://github.com/JanJaapKo/domoticz-GoodWeSEMS)
  - Changelog: [https://github.com/JanJaapKo/domoticz-GoodWeSEMS/commits](https://github.com/JanJaapKo/domoticz-GoodWeSEMS/commits)
  - Repository: [https://github.com/JanJaapKo/domoticz-GoodWeSEMS](https://github.com/JanJaapKo/domoticz-GoodWeSEMS)
  - Package: [master/make/pkgs/domoticz-goodwe/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-goodwe/)
  - Steward: Ircama

`domoticz-goodwe` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*GoodWe solar inverter (SEMS API)* plugin into the plugin directory of the hub.

Purpose: read a GoodWe inverter through the SEMS cloud API.

## Setup

Setup -> Hardware -> GoodWe, enter the account and station data of the SEMS portal.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-GoodWeSEMS` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  7 Python modules, the upstream README and its LICENSE.md.
  The images and the release archives of the GitHub page are not, and the whole
  tree moves to external storage together with `/usr/share/domoticz`;
* the plugin needs `python3-requests` in addition to the Domoticz module and the Python standard library:
  the package selects and depends on it;
* licensed upstream (LICENSE.md is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device it
  talks to, which was not available here.
