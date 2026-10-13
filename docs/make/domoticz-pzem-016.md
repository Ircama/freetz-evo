# Domoticz plugin: PZEM-016 (Modbus RS-485)
  - Homepage: [https://github.com/CreasolTech/domoticz-pzem-016](https://github.com/CreasolTech/domoticz-pzem-016)
  - Changelog: [https://github.com/CreasolTech/domoticz-pzem-016/commits](https://github.com/CreasolTech/domoticz-pzem-016/commits)
  - Repository: [https://github.com/CreasolTech/domoticz-pzem-016](https://github.com/CreasolTech/domoticz-pzem-016)
  - Package: [master/make/pkgs/domoticz-pzem-016/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-pzem-016/)
  - Steward: Ircama


`domoticz-pzem-016` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*PZEM-016 (Modbus RS-485)* plugin into the plugin directory of the hub.

Purpose: readings of the PZEM-016 energy monitors (voltage, current, power, energy) (it ships its own copy of minimalmodbus and uses pyserial for the RS-485 port).

## Setup

Setup -> Hardware -> PZEM-016, enter the serial port and the Modbus address.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-pzem-016` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-pyserial` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
