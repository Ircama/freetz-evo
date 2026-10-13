# Domoticz plugin: Quatt heat pump
  - Homepage: [https://github.com/galadril/Domoticz-Quatt-Plugin](https://github.com/galadril/Domoticz-Quatt-Plugin)
  - Changelog: [https://github.com/galadril/Domoticz-Quatt-Plugin/commits](https://github.com/galadril/Domoticz-Quatt-Plugin/commits)
  - Repository: [https://github.com/galadril/Domoticz-Quatt-Plugin](https://github.com/galadril/Domoticz-Quatt-Plugin)
  - Package: [master/make/pkgs/domoticz-quatt/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-quatt/)
  - Steward: Ircama

`domoticz-quatt` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Quatt heat pump* plugin into the plugin directory of the hub.

Purpose: read the status of a Quatt hybrid heat pump.

## Setup

Setup -> Hardware -> Quatt, enter the address of the heat pump controller.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-Quatt-Plugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream README.
  The images and the release archives of the GitHub page are not, and the whole
  tree moves to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so
  no additional Python package is needed;
* **upstream publishes no license file**, so the plugin keeps the licensing status
  upstream gave it;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device it
  talks to, which was not available here.
