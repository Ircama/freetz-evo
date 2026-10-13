# Domoticz plugin: presence detection via the FRITZ!Box
  - Homepage: [https://github.com/belzetrigger/domoticz-FritzPresence](https://github.com/belzetrigger/domoticz-FritzPresence)
  - Changelog: [https://github.com/belzetrigger/domoticz-FritzPresence/commits](https://github.com/belzetrigger/domoticz-FritzPresence/commits)
  - Repository: [https://github.com/belzetrigger/domoticz-FritzPresence](https://github.com/belzetrigger/domoticz-FritzPresence)
  - Package: [master/make/pkgs/domoticz-fritz-presence/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-fritz-presence/)
  - Steward: Ircama

`domoticz-fritz-presence` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*presence detection via the FRITZ!Box* plugin into the plugin directory of the hub.

Purpose: presence detection driven by the FRITZ!Box (devices seen by the router).

## Setup

Setup -> Hardware -> Fritz Presence, enter the address and credentials of the FRITZ!Box.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-FritzPresence` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream README and its LICENSE.
  The resource directories `blz`, `fritzhelper`, `resources` of the repository are installed too.
  The images and the release archives of the GitHub page are not, and the whole
  tree moves to external storage together with `/usr/share/domoticz`;
* the plugin needs `python3-fritzconnection` in addition to the Domoticz module and the Python standard library:
  the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device it
  talks to, which was not available here.
