# AVM-rules
  - Package: [master/make/pkgs/avm-rules/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/avm-rules/)
  - Steward: [@fda77](https://github.com/fda77)

AVM-rules can expose ports of the Fritz!Box itself, and only those ports, for access from the internet.<br>

[![screenshot](../screenshots/000-PKG_avm-rules_md.png)](../screenshots/000-PKG_avm-rules.png)

It uses ```pcplisten``` and only supports IPv4 forwards. It can be found in menuconfig under ```packages > webif```.

 * Ports are opened for at most 120 seconds and must then be renewed.
 * New ports are opened immediately when the daemon starts.
 * After configuration changes, old ports are updated only after the first interval.
 * Open ports cannot be closed explicitly; the timeout must expire.

