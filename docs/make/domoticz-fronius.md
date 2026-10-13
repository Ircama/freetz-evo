# Domoticz plugin: Fronius solar inverter
  - Homepage: [https://github.com/ayasystems/froniusHttp](https://github.com/ayasystems/froniusHttp)
  - Changelog: [https://github.com/ayasystems/froniusHttp/commits](https://github.com/ayasystems/froniusHttp/commits)
  - Repository: [https://github.com/ayasystems/froniusHttp](https://github.com/ayasystems/froniusHttp)
  - Package: [master/make/pkgs/domoticz-fronius/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-fronius/)
  - Steward: Ircama

`domoticz-fronius` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Fronius solar inverter* plugin into the plugin directory of the hub.

Purpose: read a Fronius inverter through its local HTTP API.

## Setup

Setup -> Hardware -> Fronius, enter the address of the inverter (or of its Datamanager).

## Packaging notes

* installed into `/usr/share/domoticz/plugins/froniusHttp` — the `-approot` of the
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
