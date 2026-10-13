# Domoticz plugin: WLED
  - Homepage: [https://github.com/frustreermeneer/domoticz-wled-plugin](https://github.com/frustreermeneer/domoticz-wled-plugin)
  - Changelog: [https://github.com/frustreermeneer/domoticz-wled-plugin/commits](https://github.com/frustreermeneer/domoticz-wled-plugin/commits)
  - Repository: [https://github.com/frustreermeneer/domoticz-wled-plugin](https://github.com/frustreermeneer/domoticz-wled-plugin)
  - Package: [master/make/pkgs/domoticz-wled/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-wled/)
  - Steward: Ircama


`domoticz-wled` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*WLED* plugin into the plugin directory of the hub.

Purpose: control of the LED strips running the WLED firmware (power, brightness, colour, effects) (it uses requests for the HTTP API of WLED).

## Setup

Setup -> Hardware -> WLED, enter the address of the WLED controller.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/wled` — the `-approot` of the
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
