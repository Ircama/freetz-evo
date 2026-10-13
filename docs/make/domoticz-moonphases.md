# Domoticz plugin: moon phases
  - Homepage: [https://github.com/ycahome/MoonPhases](https://github.com/ycahome/MoonPhases)
  - Changelog: [https://github.com/ycahome/MoonPhases/commits](https://github.com/ycahome/MoonPhases/commits)
  - Repository: [https://github.com/ycahome/MoonPhases](https://github.com/ycahome/MoonPhases)
  - Package: [master/make/pkgs/domoticz-moonphases/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-moonphases/)
  - Steward: Ircama

`domoticz-moonphases` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*moon phases* plugin into the plugin directory of the hub.

Purpose: create devices with the moon phase, the moonrise and the moonset.

## Setup

Setup -> Hardware -> Moon phases, then set the latitude and longitude of the location.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/MoonPhases` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream README.
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
