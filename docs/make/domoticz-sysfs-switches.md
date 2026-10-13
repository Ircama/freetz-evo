# Domoticz plugin: GPIO switches via sysfs
  - Homepage: [https://github.com/flatsiedatsie/GPIO-SYSFS-Switches](https://github.com/flatsiedatsie/GPIO-SYSFS-Switches)
  - Changelog: [https://github.com/flatsiedatsie/GPIO-SYSFS-Switches/commits](https://github.com/flatsiedatsie/GPIO-SYSFS-Switches/commits)
  - Repository: [https://github.com/flatsiedatsie/GPIO-SYSFS-Switches](https://github.com/flatsiedatsie/GPIO-SYSFS-Switches)
  - Package: [master/make/pkgs/domoticz-sysfs-switches/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-sysfs-switches/)
  - Steward: Ircama


`domoticz-sysfs-switches` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*GPIO switches via sysfs* plugin into the plugin directory of the hub.

Purpose: expose the GPIOs of the system in Domoticz as switches, reading and writing the sysfs filesystem (it reaches the GPIOs through sysfs and needs no additional Python module).

## Setup

Setup -> Hardware -> SYSFS-Switches, name the GPIOs to expose.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/SYSFS-Switches` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin imports the Domoticz module and the Python standard library only, so no additional Python package is required;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
