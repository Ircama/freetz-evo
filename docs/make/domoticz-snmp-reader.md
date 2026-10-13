# Domoticz plugin: SNMP reader
  - Homepage: [https://github.com/ycahome/SNMPreader](https://github.com/ycahome/SNMPreader)
  - Changelog: [https://github.com/ycahome/SNMPreader/commits](https://github.com/ycahome/SNMPreader/commits)
  - Repository: [https://github.com/ycahome/SNMPreader](https://github.com/ycahome/SNMPreader)
  - Package: [master/make/pkgs/domoticz-snmp-reader/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-snmp-reader/)
  - Steward: Ircama


`domoticz-snmp-reader` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*SNMP reader* plugin into the plugin directory of the hub.

Purpose: readings from SNMP v1, v2c and v3 agents (switches, printers, NAS, UPS) exposed as Domoticz sensors.

## Setup

Setup -> Hardware -> SNMP reader, enter the address of the agent, the SNMP version, the credentials or community and the OIDs to read.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/SNMPreader` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  3 Python modules, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-pysnmp` (with `python-pyasn1`) in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
