# Domoticz plugin: presence detection from the router (iDetect)
  - Homepage: [https://github.com/d-EScape/Domoticz_iDetect](https://github.com/d-EScape/Domoticz_iDetect)
  - Changelog: [https://github.com/d-EScape/Domoticz_iDetect/commits](https://github.com/d-EScape/Domoticz_iDetect/commits)
  - Repository: [https://github.com/d-EScape/Domoticz_iDetect](https://github.com/d-EScape/Domoticz_iDetect)
  - Package: [master/make/pkgs/domoticz-idetect/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz-idetect/)
  - Steward: Ircama

`domoticz-idetect` is an add-on to the [`domoticz`](domoticz.md) package: it installs the
*iDetect* plugin into the plugin directory of the hub.

Purpose: presence detection driven by the clients of the home router: the devices that
the router lists as connected are reported as present in Domoticz, so no app has to run
on the phones.

## Setup

Setup -> Hardware -> iDetect, choose the tracker of the router and enter its address and
credentials. The trackers of the repository cover FRITZ!Box (TR-064), OpenWrt (`brctl`),
RouterOS, UniFi, USG, Omada, Orbi, AiMesh, Zyxel and NETGEAR (SOAP), each over its own
protocol, plus a ping tracker for the hosts that answer ICMP; the plugin can also run in
autodetect mode.

## Packaging notes

* installed into `/usr/share/domoticz/plugins/Domoticz_iDetect` — the `-approot` of the
  Domoticz init script — together with everything the plugin needs at run time:
  `plugin.py`, `override_switch.py`, the upstream README and its images.
  The resource directories `helpers`, `trackers` and `resources` are installed too.
  The systemd units of the repository (`ihome.zip`, `ioverride.zip`, `iunit.zip`, meant
  for a Linux server) are not, and the whole tree moves to external storage together
  with `/usr/share/domoticz`;
* the plugin needs `python3-fritzconnection`, `python-paramiko`, `pynetgear` and
  `requests` in addition to the Domoticz module and the Python standard library: the
  package selects and depends on all of them. `python3-paramiko` is new in this tree and
  brings `python3-invoke` (its own new package) with it, on top of the `bcrypt`,
  `cryptography` and `pynacl` already present;
* because the plugin imports from the `helpers/` and `trackers/` subdirectories, those
  directories must keep their execute bit: the recipe chmods only the files
  (`find -type f`) and not the whole glob, which would clear the bit and break the
  import at run time;
* upstream ships no license file: the README is installed with the plugin;
* upstream has no release tags: the package version is the pinned commit of the
  default branch, checked by SHA256;
* verified: the package downloads, unpacks and installs the plugin files, and the
  Python sources pass a syntax check. Exercising the plugin needs a router of one of the
  supported families, which was not available here.

