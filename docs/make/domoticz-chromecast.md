# Domoticz plugin: Chromecast
  - Homepage: [https://github.com/Tsjippy/ChromecastPlugin](https://github.com/Tsjippy/ChromecastPlugin)
  - Changelog: [https://github.com/Tsjippy/ChromecastPlugin/commits](https://github.com/Tsjippy/ChromecastPlugin/commits)
  - Repository: [https://github.com/Tsjippy/ChromecastPlugin](https://github.com/Tsjippy/ChromecastPlugin)
  - Package: [master/make/pkgs/domoticz-chromecast/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-chromecast/)
  - Steward: Ircama


`domoticz-chromecast` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Chromecast* plugin into the plugin directory of the hub.

Purpose: discovery and control of Chromecast and Google Cast devices (media, playback state, volume).

## Setup

Setup -> Hardware -> Chromecast, enter the address of the device or let the plugin discover it.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/ChromecastPlugin` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-pychromecast` and `python-requests`: the package selects and depends on both, and pychromecast brings `protobuf`, `casttube` and `zeroconf` with it (all packaged in this tree);
* upstream ships no license file: the README is installed with the plugin;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
