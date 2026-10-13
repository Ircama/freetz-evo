# Domoticz plugin: RTSP camera bridge
  - Homepage: [https://github.com/blooesky/domoticz-camera-bridge](https://github.com/blooesky/domoticz-camera-bridge)
  - Changelog: [https://github.com/blooesky/domoticz-camera-bridge/commits](https://github.com/blooesky/domoticz-camera-bridge/commits)
  - Repository: [https://github.com/blooesky/domoticz-camera-bridge](https://github.com/blooesky/domoticz-camera-bridge)
  - Package: [master/make/pkgs/domoticz-camera-bridge/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-camera-bridge/)
  - Steward: Ircama

`domoticz-camera-bridge` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*RTSP camera bridge* plugin into the plugin directory of the hub.

Purpose: publish RTSP camera snapshots as still JPEG images for the Domoticz camera devices.

## Setup

Setup -> Hardware -> Camera bridge, add one entry per camera with its RTSP URL.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/domoticz-camera-bridge` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  2 Python modules, the upstream README and its LICENSE.
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
