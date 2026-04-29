# dnsd-cgi
  - Package: [master/make/pkgs/dnsd-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/dnsd-cgi/)
  - Steward: -

Lightweight DNS server for static name resolution (BusyBox applet).

### Further Links

-   [Man
    page](http://www.busybox.net/downloads/BusyBox.html#dnsd)

### Example Configuration

Map port 53 to 10053 with [AVM firewall CGI](avm-firewall.md), where
[iodine](iodine.md) is running. iodine forwards queries for unknown
domains to port 5353, where *dnsd* is running. *dnsd* answers these
queries for a few subdomains.

