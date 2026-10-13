# Domoticz plugin: presence detection from network devices
  - Homepage: [https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin](https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin)
  - Changelog: [https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin/commits](https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin/commits)
  - Repository: [https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin](https://github.com/blooesky/Detect-Presence-at-Home---Domoticz-plugin)
  - Package: [master/make/pkgs/domoticz-home-presence/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-home-presence/)
  - Steward: Ircama

`domoticz-home-presence` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*presence detection from network devices* plugin into the plugin directory of the hub.

Purpose: detect whether somebody is at home from the devices seen on the network.

## Setup

Setup -> Hardware -> Home presence, then list the devices that count as presence and the timeout.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Detect-Presence-at-Home` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream README.
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
