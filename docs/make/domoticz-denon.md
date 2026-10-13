# Domoticz plugin: Denon/Marantz AV receiver
  - Homepage: [https://github.com/dnpwwo/Domoticz-Denon-Plugin](https://github.com/dnpwwo/Domoticz-Denon-Plugin)
  - Changelog: [https://github.com/dnpwwo/Domoticz-Denon-Plugin/commits](https://github.com/dnpwwo/Domoticz-Denon-Plugin/commits)
  - Repository: [https://github.com/dnpwwo/Domoticz-Denon-Plugin](https://github.com/dnpwwo/Domoticz-Denon-Plugin)
  - Package: [master/make/pkgs/domoticz-denon/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-denon/)
  - Steward: Ircama

`domoticz-denon` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Denon/Marantz AV receiver* plugin into the plugin directory of the hub.

Purpose: control Denon and Marantz AV receivers over the LAN.

## Setup

Setup -> Hardware -> Denon/Marantz, enter the address of the receiver.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-Denon-Plugin` — the `-approot` of the
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
