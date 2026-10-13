# Domoticz plugin: WAN IP checker
  - Homepage: [https://github.com/ycahome/WAN-IP-CHECKER](https://github.com/ycahome/WAN-IP-CHECKER)
  - Changelog: [https://github.com/ycahome/WAN-IP-CHECKER/commits](https://github.com/ycahome/WAN-IP-CHECKER/commits)
  - Repository: [https://github.com/ycahome/WAN-IP-CHECKER](https://github.com/ycahome/WAN-IP-CHECKER)
  - Package: [master/make/pkgs/domoticz-wan-ip-checker/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-wan-ip-checker/)
  - Steward: Ircama

`domoticz-wan-ip-checker` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*WAN IP checker* plugin into the plugin directory of the hub.

Purpose: watch the public IP address of the WAN connection and alert on changes.

## Setup

Setup -> Hardware -> WAN IP checker, choose the check interval.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/WAN-IP-CHECKER` — the `-approot` of the
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
