# Domoticz plugin: NUT UPS monitor
  - Homepage: [https://github.com/999LV/NUT_UPS](https://github.com/999LV/NUT_UPS)
  - Changelog: [https://github.com/999LV/NUT_UPS/commits](https://github.com/999LV/NUT_UPS/commits)
  - Repository: [https://github.com/999LV/NUT_UPS](https://github.com/999LV/NUT_UPS)
  - Package: [master/make/pkgs/domoticz-nut-ups/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-nut-ups/)
  - Steward: Ircama

`domoticz-nut-ups` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*NUT UPS monitor* plugin into the plugin directory of the hub.

Purpose: monitor a UPS through a NUT (network ups tools) server.

## Setup

Setup -> Hardware -> UPS monitor, enter the NUT server address, then the UPS name and credentials.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/NUT_UPS` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream README and its LICENSE.
  The images and the release archives of the GitHub page are not, and the whole
  tree moves to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so
  no additional Python package is needed;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device it
  talks to, which was not available here.
