# Domoticz plugin: alphaESS battery
  - Homepage: [https://github.com/AntoineVDH/alphaESS-battery-plugin](https://github.com/AntoineVDH/alphaESS-battery-plugin)
  - Changelog: [https://github.com/AntoineVDH/alphaESS-battery-plugin/commits](https://github.com/AntoineVDH/alphaESS-battery-plugin/commits)
  - Repository: [https://github.com/AntoineVDH/alphaESS-battery-plugin](https://github.com/AntoineVDH/alphaESS-battery-plugin)
  - Package: [master/make/pkgs/domoticz-alphaess/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-alphaess/)
  - Steward: Ircama

`domoticz-alphaess` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*alphaESS battery* plugin into the plugin directory of the hub.

Purpose: battery status of an alphaESS storage system through its cloud API.

## Setup

Setup -> Hardware -> alphaESS, enter the credentials of the alphaESS portal.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/alphaESS-battery-plugin` — the `-approot` of the
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
