# Domoticz plugin: sync timer
  - Homepage: [https://github.com/skarab22/Domoticz-sync-timer](https://github.com/skarab22/Domoticz-sync-timer)
  - Changelog: [https://github.com/skarab22/Domoticz-sync-timer/commits](https://github.com/skarab22/Domoticz-sync-timer/commits)
  - Repository: [https://github.com/skarab22/Domoticz-sync-timer](https://github.com/skarab22/Domoticz-sync-timer)
  - Package: [master/make/pkgs/domoticz-sync-timer/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-sync-timer/)
  - Steward: Ircama


`domoticz-sync-timer` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*sync timer* plugin into the plugin directory of the hub.

Purpose: periodic synchronisation of timers and switches between Domoticz and external devices (it uses requests for the endpoints it synchronises).

## Setup

Setup -> Hardware -> sync timer, enter the broker and the devices to synchronise.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Update_timer` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-requests` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* upstream ships no license file: the README is installed with the plugin;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
