# VTun 3.0.4 - DEPRECATED
  - Package: [master/make/pkgs/vtun/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/vtun/)
  - Steward: -

[VTUN](http://vtun.sourceforge.net/) is a
simple way to build a tunnel from or to the Fritzbox. At a maximum of 75k,
it is also not very large.

### Version

[![vtun configuration GUI](../screenshots/125_md.png)](../screenshots/125.png)

Version 3.0.2 is currently included. It can be built in menuconfig
(currently in the "Testing" section) with the following options:

-   Compression via LZO2 or Deflate (zlib)
-   Encryption via SSL (caution: [note the information about the SSL
  library](../wiki/00_FAQ/FAQ.html))
  ^It is possible to build VTUN statically to avoid possible problems with this^
-   Flow control ("traffic shaping")

### Configuration Guide

The GUI for the program is currently very simple:

-   The invocation string for the program is defined in one line.
-   The configuration file is entered in the field below.

The VTUN site also provides a few
[configuration examples](http://vtun.sourceforge.net/setup.html).

### Port Forwarding

If the box is to act as a server and the connection to the box is to be
established over the internet, port forwarding must be configured for
this. The topic is covered in detail, for example, in the
[OpenVPN](openvpn.html#port-forwarding) package documentation. For Freetz
users, the [AVM Firewall](avm-firewall.md) package is a suitable option.

