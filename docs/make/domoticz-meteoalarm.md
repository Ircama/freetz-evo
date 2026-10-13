# Domoticz plugin: MeteoAlarm EU
  - Homepage: [https://github.com/ycahome/MeteoAlarmEU](https://github.com/ycahome/MeteoAlarmEU)
  - Changelog: [https://github.com/ycahome/MeteoAlarmEU/commits](https://github.com/ycahome/MeteoAlarmEU/commits)
  - Repository: [https://github.com/ycahome/MeteoAlarmEU](https://github.com/ycahome/MeteoAlarmEU)
  - Package: [master/make/pkgs/domoticz-meteoalarm/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-meteoalarm/)
  - Steward: Ircama


`domoticz-meteoalarm` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*MeteoAlarm EU* plugin into the plugin directory of the hub.

Purpose: European weather alerts (MeteoAlarm) as sensors and notifications in Domoticz (it reads the feeds with feedparser).

## Setup

Setup -> Hardware -> MeteoAlarmEU, enter the region and the feed to follow.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/MeteoAlarmEU` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  1 Python module, the upstream documentation.
  The remaining files of the repository are not installed, and the whole tree moves
  to external storage together with `/usr/share/domoticz`;
* the plugin needs `python-feedparser` in addition to the Domoticz module and the Python standard library: the package selects and depends on it;
* licensed upstream (LICENSE is installed with the plugin);
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs the device or the
  service it talks to, which was not available here.
