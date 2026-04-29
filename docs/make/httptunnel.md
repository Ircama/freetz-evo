# httptunnel 3.3 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/httptunnel/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/httptunnel/)
  - Steward: -

**[httptunnel](http://www.nocrew.org/software/httptunnel.html)**
creates a virtual, bidirectional data connection tunneled over the HTTP
protocol. The required HTTP requests can also be routed through proxies
if needed.

This approach is useful for anyone behind a restrictive firewall. As long
as web access is allowed, even if only through a proxy, *httptunnel* can
be used, for example, to access a computer outside the firewall via
Telnet.

A somewhat more illustrative example follows, by
[sweetie-pie](http://www.ip-phone-forum.de/member.php?u=62645)
from [this
Thread](http://www.ip-phone-forum.de/showthread.php?p=536622#post536622):

```
PC at the company        Proxy at the company       Fritzbox

    +-------+    Connected to                        +-------+    home network
   |Putty  |--+ 127.0.0.1:22                        |sshd   |--> via ssh-Tunnel
   |-------|  |                +-----+              |       |<-+ (Port 22)
   |htc    |<-+ Port 22        |HTTP |              |-------|  |
   |       |------------------>|Proxy|------------->|hts    |--+
   +-------+                   +-----+    Port 9999 +-------+
```

Currently, httptunnel is available for Freetz only as a binary (3.3), so
there is no WebGUI for graphical settings yet.

### Further Links

-   [httptunnel
    Homepage](http://www.nocrew.org/software/httptunnel.html)
-   [Mini-how-to at
    LinuxWiki.org](http://linuxwiki.org/HttpTunnel)
-   [Wikipedia article on HTTP
    Tunneling](http://en.wikipedia.org/wiki/HTTP_tunnel)
    (English)
-   [Thread in the
    IP-Phone-Forum](http://www.ip-phone-forum.de/showthread.php?t=167980)

