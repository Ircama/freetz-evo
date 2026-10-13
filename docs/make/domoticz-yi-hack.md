# Domoticz plugin: Yi camera with yi-hack firmware
  - Homepage: [https://github.com/galadril/Domoticz-Yi-Hack-Plugin](https://github.com/galadril/Domoticz-Yi-Hack-Plugin)
  - Changelog: [https://github.com/galadril/Domoticz-Yi-Hack-Plugin/commits](https://github.com/galadril/Domoticz-Yi-Hack-Plugin/commits)
  - Repository: [https://github.com/galadril/Domoticz-Yi-Hack-Plugin](https://github.com/galadril/Domoticz-Yi-Hack-Plugin)
  - Package: [master/make/pkgs/domoticz-yi-hack/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-yi-hack/)
  - Steward: Ircama

`domoticz-yi-hack` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Yi camera with yi-hack firmware* plugin into the plugin directory of the hub.

Purpose: control Xiaomi Yi cameras with the yi-hack firmware (snapshots, motion events).

## Setup

Setup -> Hardware -> Yi Hack, enter the address of each camera.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-Yi-Hack-Plugin` — the `-approot` of the
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
