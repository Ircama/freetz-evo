# Domoticz plugin: HomeWizard Wi-Fi water meter
  - Homepage: [https://github.com/Eraser3/HomeWizard-Wifi-Watermeter](https://github.com/Eraser3/HomeWizard-Wifi-Watermeter)
  - Changelog: [https://github.com/Eraser3/HomeWizard-Wifi-Watermeter/commits](https://github.com/Eraser3/HomeWizard-Wifi-Watermeter/commits)
  - Repository: [https://github.com/Eraser3/HomeWizard-Wifi-Watermeter](https://github.com/Eraser3/HomeWizard-Wifi-Watermeter)
  - Package: [master/make/pkgs/domoticz-hw-watermeter/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-hw-watermeter/)
  - Steward: Ircama

`domoticz-hw-watermeter` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*HomeWizard Wi-Fi water meter* plugin into the plugin directory of the hub.

Purpose: read a HomeWizard Wi-Fi water meter over the LAN.

## Setup

Setup -> Hardware -> HomeWizard water meter, enter the IP address of the meter.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/HomeWizard-Wifi-Watermeter` — the `-approot` of the
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
