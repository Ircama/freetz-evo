# Domoticz plugin: Xiaomi robot vacuum
  - Homepage: [https://github.com/mrin/domoticz-mirobot-plugin](https://github.com/mrin/domoticz-mirobot-plugin)
  - Changelog: [https://github.com/mrin/domoticz-mirobot-plugin/commits](https://github.com/mrin/domoticz-mirobot-plugin/commits)
  - Repository: [https://github.com/mrin/domoticz-mirobot-plugin](https://github.com/mrin/domoticz-mirobot-plugin)
  - Package: [master/make/pkgs/domoticz-xiaomi-robot-vacuum/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-xiaomi-robot-vacuum/)
  - Steward: Ircama


`domoticz-xiaomi-robot-vacuum` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Xiaomi robot vacuum* plugin into the plugin directory of the hub.

Purpose: control of the Xiaomi and roborock robot vacuums (start, stop, return to base, status, battery).

## Setup

Setup -> Hardware -> Xiaomi MI Robot, enter the address and the token of the vacuum.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/xiaomi-mirobot` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  3 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-gevent`, `python-msgpack` and `python-miio` in addition to the Domoticz module and the Python standard library: gevent is built against the `libev` and `libcares` of this tree;
* upstream ships no license file: the README is installed with the plugin;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
