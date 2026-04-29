# Addhole (for dnsmasq)
  - Package: [master/make/pkgs/addhole/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/addhole/)
  - Steward: [@fda77](https://github.com/fda77)

Addhole is an extension for Dnsmasq.<br>

[![screenshot](../screenshots/000-PKG_addhole_md.png)](../screenshots/000-PKG_addhole.png)

 - Addhole can include lists of hostnames in Dnsmasq and block them. There are lists of hosts that distribute advertising, malware, viruses, and similar unwanted content.
   The package is comparable to Pi-hole, but without the web interface with access statistics and without requiring an additional device.

 - With Addhole's default configuration, Dnsmasq needs about 10 MB of RAM; with all predefined lists enabled, it needs about 25 MB of RAM.
   Note: this makes no sense on a Fritzbox with 32 MB of RAM.
   The lists can be updated automatically with Cron. Additional custom hosts can also be specified.

 - Caution: name resolution is cached on the server (Dnsmasq), on the client (Linux, Windows, Android, ...), and in the application program (for example, the web browser).
   If a change is not visible immediately, clear all caches, or simply reboot everything.

