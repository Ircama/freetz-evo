# Domoticz plugin: ebusd heating bridge
  - Homepage: [https://github.com/guillaumezin/DomoticzEbusd](https://github.com/guillaumezin/DomoticzEbusd)
  - Changelog: [https://github.com/guillaumezin/DomoticzEbusd/commits](https://github.com/guillaumezin/DomoticzEbusd/commits)
  - Repository: [https://github.com/guillaumezin/DomoticzEbusd](https://github.com/guillaumezin/DomoticzEbusd)
  - Package: [master/make/pkgs/domoticz-ebusd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-ebusd/)
  - Steward: Ircama

`domoticz-ebusd` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*ebusd heating bridge* plugin into the plugin directory of the hub.

Purpose: read a heating system through an ebusd daemon (Vaillant, Wolf, ...).

## Setup

Setup -> Hardware -> ebusd, enter the address and port of the ebusd daemon.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/DomoticzEbusd` — the `-approot` of the
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
