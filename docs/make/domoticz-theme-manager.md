# Domoticz plugin: theme manager
  - Homepage: [https://github.com/galadril/domoticz-theme-manager](https://github.com/galadril/domoticz-theme-manager)
  - Changelog: [https://github.com/galadril/domoticz-theme-manager/commits](https://github.com/galadril/domoticz-theme-manager/commits)
  - Repository: [https://github.com/galadril/domoticz-theme-manager](https://github.com/galadril/domoticz-theme-manager)
  - Package: [master/make/pkgs/domoticz-theme-manager/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-theme-manager/)
  - Steward: Ircama

`domoticz-theme-manager` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*theme manager* plugin into the plugin directory of the hub.

Purpose: install and update the web interface themes of Domoticz from its own page.

## Setup

Use the page registered in the Domoticz web interface to install a theme.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-theme-manager` — the `-approot` of the
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
