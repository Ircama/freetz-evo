# Domoticz plugin: KNMI weather (NL)
  - Homepage: [https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin](https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin)
  - Changelog: [https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin/commits](https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin/commits)
  - Repository: [https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin](https://github.com/bramvreugd/Domoticz-KNMI-Weather-Plugin)
  - Package: [master/make/pkgs/domoticz-knmi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-knmi/)
  - Steward: Ircama

`domoticz-knmi` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*KNMI weather (NL)* plugin into the plugin directory of the hub.

Purpose: read the KNMI (Dutch weather service) forecast and warnings.

## Setup

Setup -> Hardware -> KNMI, enter the location and the API key.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz-KNMI-Weather-Plugin` — the `-approot` of the
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
