# Domoticz plugin: Dahua VTO door intercom
  - Homepage: [https://github.com/rbrouwer/dahua-vto-dz](https://github.com/rbrouwer/dahua-vto-dz)
  - Changelog: [https://github.com/rbrouwer/dahua-vto-dz/commits](https://github.com/rbrouwer/dahua-vto-dz/commits)
  - Repository: [https://github.com/rbrouwer/dahua-vto-dz](https://github.com/rbrouwer/dahua-vto-dz)
  - Package: [master/make/pkgs/domoticz-dahua-vto/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-dahua-vto/)
  - Steward: Ircama

`domoticz-dahua-vto` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Dahua VTO door intercom* plugin into the plugin directory of the hub.

Purpose: read a Dahua VTO door intercom (calls, door release, snapshots).

## Setup

Setup -> Hardware -> Dahua VTO, enter the address and the credentials of the intercom.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/dahua-vto-dz` — the `-approot` of the
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
