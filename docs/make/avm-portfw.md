# AVM-portfw
  - Package: [master/make/pkgs/avm-portfw/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/avm-portfw/)
  - Steward: [@fda77](https://github.com/fda77)

AVM-portfw can expose ports of the Fritz!Box itself, and only those ports, for access from the internet.<br>

[![screenshot](../screenshots/000-PKG_avm-portfw_md.png)](../screenshots/000-PKG_avm-portfw.png)

It uses ```internet_forwardrules``` and only supports IPv4 forwards. It can be found in menuconfig under ```packages > webif```.
Because ```ar7.cfg``` is modified, create a complete backup first - EXPERIMENTAL!

 * Specify port blocks as PORT+COUNT, for example 55500+3 for 55500-55502.
 * Specify redirects as EXTERNAL(+COUNT):INTERNAL, for example 443:8443 or 80+2:8008.
 * The entries can be checked in the AVM web interface under Diagnosis > Security.
 * If there are syntax errors, AVM resets the complete ar7.cfg.

