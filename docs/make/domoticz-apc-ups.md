# Domoticz plugin: APC UPS monitor
  - Homepage: [https://github.com/jgaalen/domoticz-apc-ups-plugin](https://github.com/jgaalen/domoticz-apc-ups-plugin)
  - Changelog: [https://github.com/jgaalen/domoticz-apc-ups-plugin/commits](https://github.com/jgaalen/domoticz-apc-ups-plugin/commits)
  - Repository: [https://github.com/jgaalen/domoticz-apc-ups-plugin](https://github.com/jgaalen/domoticz-apc-ups-plugin)
  - Package: [master/make/pkgs/domoticz-apc-ups/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-apc-ups/)
  - Steward: Ircama

`domoticz-apc-ups` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*APC UPS monitor* plugin into the plugin directory of the hub.

Purpose: monitor an APC UPS through the apcupsd daemon or its SNMP interface.

## Setup

Setup -> Hardware -> APC UPS, enter the address and the community of the UPS.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-apc-ups-plugin` — the `-approot` of the
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
