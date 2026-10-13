# Domoticz plugin: Linky smart meter (FR, Enedis account)
  - Homepage: [https://github.com/guillaumezin/DomoticzLinky](https://github.com/guillaumezin/DomoticzLinky)
  - Changelog: [https://github.com/guillaumezin/DomoticzLinky/commits](https://github.com/guillaumezin/DomoticzLinky/commits)
  - Repository: [https://github.com/guillaumezin/DomoticzLinky](https://github.com/guillaumezin/DomoticzLinky)
  - Package: [master/make/pkgs/domoticz-linky/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-linky/)
  - Steward: Ircama

`domoticz-linky` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*Linky smart meter (FR)* plugin into the plugin directory of the hub.

Purpose: consumption of a Linky (French) smart meter read from the Enedis web services
of the distribution network operator.

It reads the hourly data of an **Enedis account** (the same figures as the Enedis web
site), **not** the teleinformation output of the meter. Domoticz has a native Teleinfo
driver (`HTYPE_TeleinfoMeter`, `HTYPE_TeleinfoMeterTCP`) for the local serial/TCP
reading, so the two do not overlap: this plugin also works when the box is far from the
meter or the meter has no local output wired to it.

## Setup

Setup -> Hardware -> Linky, enter the Enedis account data. An Enedis account is needed
and the plugin uses a public proxy for the Enedis authentication; upstream states that
support and updates will probably be very limited.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/DomoticzLinky` — the `-approot` of the
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
  Python sources pass a syntax check. Exercising the plugin needs an Enedis account,
  which was not available here.
