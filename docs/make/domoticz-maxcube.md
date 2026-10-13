# Domoticz plugin: eQ-3 MAX! heating system
  - Homepage: [https://github.com/mvzut/maxcube-Domoticz-plugin](https://github.com/mvzut/maxcube-Domoticz-plugin)
  - Changelog: [https://github.com/mvzut/maxcube-Domoticz-plugin/commits](https://github.com/mvzut/maxcube-Domoticz-plugin/commits)
  - Repository: [https://github.com/mvzut/maxcube-Domoticz-plugin](https://github.com/mvzut/maxcube-Domoticz-plugin)
  - Package: [master/make/pkgs/domoticz-maxcube/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-maxcube/)
  - Steward: Ircama

`domoticz-maxcube` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*eQ-3 MAX! heating system* plugin into the plugin directory of the hub.

Purpose: control an eQ-3 MAX! Cube heating system (thermostats, wall thermostats, window contacts).

## Setup

Setup -> Hardware -> MAX! Cube, enter the IP address of the cube.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/maxcube-Domoticz-plugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream README.
  The resource directories `maxcube` of the repository are installed too.
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
