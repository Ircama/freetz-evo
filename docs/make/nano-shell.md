# Nano Shell 0.1 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/nano-shell/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nano-shell/)
  - Steward: -

The **Nano Shell** executes arbitrary shell commands via URL, meaning
that parameters appended to a web address are evaluated by a small CGI
script. Nano Shell is even smaller and lighter than the
[Rudi Shell](rudi-shell.md), because it does not need an entry interface.
The following quotes the help text from `make menuconfig`, supplemented
with some additional information:

This small package enables both the AVM and Freetz web interfaces to run
user-defined shell commands and display their command or error output, if
any.

### Security Notice

 * **ATTENTION!**
Nano Shell should be used only for debugging purposes (development,
troubleshooting), for example when *telnetd*, *sshd (Dropbear)*, or
*Rudi Shell* is unavailable or inaccessible for some reason. It is a kind
of reserve parachute or last resort for running commands on the router
box when everything else fails, but at least one of the two web
interfaces (AVM or Freetz) is still accessible.
/!

Since Nano Shell bypasses the password prompt in the AVM interface, this
is a
/!
***potential security risk***
/!, sofern Ihre
router box is accessible to strangers from the LAN/WAN. The Freetz
password is requested, however, because it already applies at the web
server level and is not implemented in the web application logic as it is
with AVM.

### Usage

Simply send a URL-encoded command to the Nano CGI, which can have, for
example, the following base addresses:

-   [http://fritz.box/cgi-bin/shell.cgi](http://fritz.box/cgi-bin/shell.cgi)
    (AVM web interface)
-   [http://speedport.ip/cgi-bin/shell.cgi](http://speedport.ip/cgi-bin/shell.cgi)
    (AVM)
-   [http://192.168.0.1/cgi-bin/shell.cgi](http://192.168.0.1/cgi-bin/shell.cgi)
    (AVM)
-   [http://fritz.box:81/cgi-bin/shell.cgi](http://fritz.box:81/cgi-bin/shell.cgi)
    (Freetz web interface)
-   [http://speedport.ip:81/cgi-bin/shell.cgi](http://speedport.ip:81/cgi-bin/shell.cgi)
    (Freetz)
-   [http://192.168.0.1:81/cgi-bin/shell.cgi](http://192.168.0.1:81/cgi-bin/shell.cgi)
    (Freetz)

or, more generally, the name or IP address under which your router box is
reachable on the network.

Some example commands with their corresponding encoded URLs:

  ---------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    Command                                                         URL
  ls -l /var/tmp                                                   [http://fritz.box/cgi-bin/shell.cgi?ls%20-l%20%2Fvar%2Ftmp](http://fritz.box/cgi-bin/shell.cgi?ls%20-l%20%2Fvar%2Ftmp)
  /usr/sbin/telnetd -p 2323 -l /bin/sh                             [http://fritz.box/cgi-bin/shell.cgi?%2Fusr%2Fsbin%2Ftelnetd%20-p%202323%20-l%20%2Fbin%2Fsh](http://fritz.box/cgi-bin/shell.cgi?%2Fusr%2Fsbin%2Ftelnetd%20-p%202323%20-l%20%2Fbin%2Fsh)
    echo "First command"; cat /etc/motd; echo "Third command"   [http://fritz.box/cgi-bin/shell.cgi?echo%20%22First%20command%22%3B%20cat%20%2Fetc%2Fmotd%3B%20echo%20%22Third%20command%22](http://fritz.box/cgi-bin/shell.cgi?echo%20%22First%20command%22%3B%20cat%20%2Fetc%2Fmotd%3B%20echo%20%22Third%20command%22)
  ---------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

There are **online encoders/decoders** for URLs on the web, for example
this
[URL-En-/Decoder](http://netzreport.googlepages.com/online_tool_zur_url_kodierung_de.html#kodieren),
which supports ASCII and UTF-8, or this
[Encoder](http://www.simplelogic.com/Developer/InetEncode.asp)
and
[Decoder](http://www.simplelogic.com/Developer/URLDecode.asp),
which encode/decode special characters in Latin-1 (ISO-8859-1). URL
decoding can also be done via BusyBox with `httpd -d STRING`.

**Usability tip** (tested in IE 7, Opera 9.23, Firefox 2.0.6, Konqueror
3.5.8): Many browsers also accept unencoded CGI parameters, meaning
commands in plain text. Normally, instead of the encoded commands above,
you can also write the following:

```
http://fritz.box/cgi-bin/shell.cgi?ls -l /var/tmp
http://fritz.box/cgi-bin/shell.cgi?/usr/sbin/telnetd -p 2323 -l /bin/sh
http://fritz.box/cgi-bin/shell.cgi?echo "First command"; cat /etc/motd; echo "Third command"
```

Have fun trying it out!

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)

