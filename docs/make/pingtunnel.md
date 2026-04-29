# Pingtunnel 0.72 - DEPRECATED
  - Package: [master/make/pkgs/pingtunnel/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/pingtunnel/)
  - Steward: -

**PTunnel** allows reliable tunneling of TCP connections over
[ICMP](http://de.wikipedia.org/wiki/Internet_Control_Message_Protocol)
echo requests, which is also known as an [ICMP
tunnel](http://en.wikipedia.org/wiki/Pingtunnel).
This may look rather useless at first glance, but it proves quite helpful
in some situations, namely when nothing else helps because a restrictive
firewall is in the way.

### Setup

Add the following to `forwardrules` in ar7.cfg to allow pings from the
internet:

```
"icmp 0.0.0.0 0.0.0.0 0 # PTunnel"
```

Or use [AVM-Firewall](avm-firewall.md) from revision 6794 to do
the same from a web interface.

Capturing packets
([libpcap](http://www.tcpdump.org/pcap3_man.html))
from interface *dsl* doesn't work (packets are fragmented), but from
interface *lan* does:

```
ptunnel -c lan
```

(Error message if using dsl: "*Received fragmented packet - unable to
reconstruct! This error usually occurs because pcap is used on devices
that are not wlan or ethernet.*")

The web interface of pingtunnel (from revision 6792) uses the following
options if you don't specify extra options:

```
-c lan -syslog -x <password>
```

For maximum flexibility `-c lan -syslog` is omitted if you specify extra
options.

Be sure to specify enough tunnels when tunneling `http` traffic with the
`-m` option.

### Security

Pingtunnel is not very secure, because it possible to choose random
tunnel endpoints from the client. The best thing that can be done, is
using a strong password.

Be sure to use client version 0.71 or higher and the patched 0.71 server
version when using passwords!

Also realize that ICMP traffic makes it to the internal net of the box
if you configure ICMP forwarding.

It is easily overlooked, but you can tighten security with these option:

```
    -da: Set remote proxy destination address if client
         Restrict to only this destination address if server
    -dp: Set remote proxy destionation port if client
         Restrict to only this destination port if server
```

You can restrict access to for example [Polipo?] like
this:

```
-da localhost -dp 8123
```

### Further Links

-   [Homepage](http://www.cs.uit.no/~daniels/PingTunnel/)
    (English)
-   [Freshmeat
    project page](http://freshmeat.net/projects/ptunnel/)
-   [Breaking through firewalls with a ping
    tunnel](http://psung.blogspot.com/2008/05/breaking-through-firewalls-with-ping.html)
    (blog article)


