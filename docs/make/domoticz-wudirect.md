# Domoticz plugin: local weather station (WuDirect)
  - Homepage: [https://github.com/vaneeten/domoticz-wudirect](https://github.com/vaneeten/domoticz-wudirect)
  - Changelog: [https://github.com/vaneeten/domoticz-wudirect/commits](https://github.com/vaneeten/domoticz-wudirect/commits)
  - Repository: [https://github.com/vaneeten/domoticz-wudirect](https://github.com/vaneeten/domoticz-wudirect)
  - Package: [master/make/pkgs/domoticz-wudirect/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-wudirect/)
  - Steward: Ircama

`domoticz-wudirect` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*local weather station (WuDirect)* plugin into the plugin directory of the hub.

Purpose: receive a local weather station that sends Weather Underground formatted data.

## Setup

Setup -> Hardware -> WuDirect, enter the UDP port to listen on and map the fields of the station.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-wudirect` — the `-approot` of the
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
