# Domoticz plugin: Synology Surveillance Station
  - Homepage: [https://github.com/lolautruche/SurveillanceStationDomoticz](https://github.com/lolautruche/SurveillanceStationDomoticz)
  - Changelog: [https://github.com/lolautruche/SurveillanceStationDomoticz/commits](https://github.com/lolautruche/SurveillanceStationDomoticz/commits)
  - Repository: [https://github.com/lolautruche/SurveillanceStationDomoticz](https://github.com/lolautruche/SurveillanceStationDomoticz)
  - Package: [master/make/pkgs/domoticz-synology/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-synology/)
  - Steward: Ircama

`domoticz-synology` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Synology Surveillance Station* plugin into the plugin directory of the hub.

Purpose: read the cameras and the events of a Synology Surveillance Station.

## Setup

Setup -> Hardware -> Synology Surveillance Station, enter the address and credentials of the NAS.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/SurveillanceStationDomoticz` — the `-approot` of the
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
