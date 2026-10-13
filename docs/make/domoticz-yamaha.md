# Domoticz plugin: Yamaha AV receiver
  - Homepage: [https://github.com/thomas-villagers/domoticz-yamaha](https://github.com/thomas-villagers/domoticz-yamaha)
  - Changelog: [https://github.com/thomas-villagers/domoticz-yamaha/commits](https://github.com/thomas-villagers/domoticz-yamaha/commits)
  - Repository: [https://github.com/thomas-villagers/domoticz-yamaha](https://github.com/thomas-villagers/domoticz-yamaha)
  - Package: [master/make/pkgs/domoticz-yamaha/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-yamaha/)
  - Steward: Ircama

`domoticz-yamaha` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Yamaha AV receiver* plugin into the plugin directory of the hub.

Purpose: control Yamaha AV receivers over the LAN, with a Kodi remote.

## Setup

Setup -> Hardware -> Yamaha, enter the address of the receiver.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-yamaha` — the `-approot` of the
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
