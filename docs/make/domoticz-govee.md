# Domoticz plugin: Govee devices (LAN discovery)
  - Homepage: [https://github.com/galadril/Domoticz-Govee-Plugin](https://github.com/galadril/Domoticz-Govee-Plugin)
  - Changelog: [https://github.com/galadril/Domoticz-Govee-Plugin/commits](https://github.com/galadril/Domoticz-Govee-Plugin/commits)
  - Repository: [https://github.com/galadril/Domoticz-Govee-Plugin](https://github.com/galadril/Domoticz-Govee-Plugin)
  - Package: [master/make/pkgs/domoticz-govee/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-govee/)
  - Steward: Ircama

`domoticz-govee` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Govee devices (LAN discovery)* plugin into the plugin directory of the hub.

Purpose: discover Govee devices on the local network and create their Domoticz devices.

## Setup

Setup -> Hardware -> Govee, let the plugin discover the devices on the LAN.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-Govee-Plugin` — the `-approot` of the
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
