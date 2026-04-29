# Virtual IP CGI - DEPRECATED
  - Package: [master/make/pkgs/virtualip-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/virtualip-cgi/)
  - Steward: -

[![VirtualIP: settings](../screenshots/61_md.png)](../screenshots/61.png)

**Virtual IP** is an extension for Freetz that makes it possible to
create a virtual IP on the box. The package can be configured through the
Freetz web interface. Initially, this virtual IP was used to be able to
create port forwards to the box in the AVM web interface.

 * **CAUTION**

This package is no longer supported and [AVM-Firewall](avm-firewall.md)
should be used instead.

Port forwards to virtual IPs no longer work reliably with firmwares
(> 04.57). With some firmwares (> 04.80), the box is sometimes no longer
reachable over the network as soon as a virtual IP has been configured.
ATA mode causes fewer problems than DSL mode.

Further links on this:

-   [IPPF: On which boxes does Virtual IP no longer work?](http://www.ip-phone-forum.de/showthread.php?t=174245)
-   [IPPF: Port forwarding to the box is possible this way; Virtual IP
    unnecessary?!?](http://www.ip-phone-forum.de/showthread.php?t=159266)

### Setup

-   **Start type**: "Automatic" if *VirtualIP* should also become active
    automatically after a reboot.
-   **Virtual IP address**: The additional IP under which the box should
    be reachable.
-   **Subnet mask**: The matching
    [subnet](http://de.wikipedia.org/wiki/Subnetz) mask. If necessary,
    also consult the [English](http://en.wikipedia.org/wiki/Subnet_mask)
    or [German](http://de.wikipedia.org/wiki/Subnetz) Wikipedia article.
-   **Interface**: Usually "eth0:1" if the box also performs DSL dial-in,
    or "dsl:0" in ATA mode. If in doubt, try a little.

Questions and discussions about this package can also be posted/conducted
[here](http://www.ip-phone-forum.de/showthread.php?t=111623).

### Known Problems and Bugs

### dsld Syslog Message

Error message in syslog:

```
user.err dsld[1243]: internet: 192.168.178.253 not an intern host, forwardrule "tcp 0.0.0.0:85 192.168.178.253:85 0 # Test" ignored
```

In **dsld**, which handles DSL and port forwarding, AVM built in a
protection mechanism that prevents forwarding to the FritzBox's own IPs.

### Problems with OpenVPN / UDP

A forward for OpenVPN or for a UDP port appears to cause problems. In any
case, it does not work for some users.

### Problems with IPTV

When Virtual IP is active, the TV signal is no longer forwarded to the
media receiver.

### Problems with SIP Registrar Mode

If a Fritzbox running on the virtual IP is used as a registrar, VoIP
calls fail at the SIP client. Outgoing packets are correctly transmitted
to the registrar, but the client waits in vain for packets from the
virtual IP. If virtual-ip is disabled and 'voipcfgchanged' is called,
everything works correctly. Tested with firmware 4.80 and Freetz 1.1.3.
