# Domoticz plugin: SmogTok air quality monitor
  - Homepage: [https://github.com/smogtok/smogtokdomoticzplug](https://github.com/smogtok/smogtokdomoticzplug)
  - Changelog: [https://github.com/smogtok/smogtokdomoticzplug/commits](https://github.com/smogtok/smogtokdomoticzplug/commits)
  - Repository: [https://github.com/smogtok/smogtokdomoticzplug](https://github.com/smogtok/smogtokdomoticzplug)
  - Package: [master/make/pkgs/domoticz-smogtok/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-smogtok/)
  - Steward: Ircama

`domoticz-smogtok` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*SmogTok air quality monitor* plugin into the plugin directory of the hub.

Purpose: read a SmogTok air quality monitor over the LAN.

## Setup

Setup -> Hardware -> SmogTok, enter the address of the monitor.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/smogtokdomoticzplug` — the `-approot` of the
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
