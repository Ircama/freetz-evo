# Domoticz plugin: Sony Bravia TV
  - Homepage: [https://github.com/gerard33/sony-bravia](https://github.com/gerard33/sony-bravia)
  - Changelog: [https://github.com/gerard33/sony-bravia/commits](https://github.com/gerard33/sony-bravia/commits)
  - Repository: [https://github.com/gerard33/sony-bravia](https://github.com/gerard33/sony-bravia)
  - Package: [master/make/pkgs/domoticz-sony-bravia/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-sony-bravia/)
  - Steward: Ircama

`domoticz-sony-bravia` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Sony Bravia TV* plugin into the plugin directory of the hub.

Purpose: control Sony Bravia televisions over the LAN, with a Kodi remote.

## Setup

Setup -> Hardware -> Sony Bravia, enter the address of the television and its pre-shared key.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/sony-bravia` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  4 Python modules, the upstream README.
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
