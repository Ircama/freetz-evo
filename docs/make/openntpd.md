# Openntpd 3.9p1 - DEPRECATED
  - Package: [master/make/pkgs/openntpd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/openntpd/)
  - Steward: -

*"OpenNTPD is a free and easy-to-use implementation of the Network Time
Protocol. OpenNTPD can synchronize the local clock with NTP servers and
also act as an NTP server itself, making the local time available to
other systems."*
[http://www.openntpd.org/de/](http://www.openntpd.org/de/)

With **OpenNTPD**, time can be synchronized via the internet. Of course,
this can also be done from any PC, and the Fritzbox itself (the multid
daemon) also gets its time from the network, so why this package?

The OpenNTPD package provides not only a client but also a server. This
allows the FritzBox to "download" the time from the internet and then
make it available in the local network.

### Advantages:

-   Only the FritzBox has to synchronize the time remotely.
-   Because the FritzBox is usually running around the clock, this can
    happen at any time, and the current time is still available if the
    internet is ever "broken" (provider problems, etc.).
-   All computers in the local network synchronize with the FritzBox and
    therefore have identical timestamps, which is very useful, for
    example, when comparing log files.
-   Even computers that are not allowed to access the internet can still
    synchronize their time.

### Ubuntu client setup

-   Install: *sudo apt-get install ntp*
-   Configure: *add server fritz.box* as first server to */etc/ntp.conf*
-   Apply configuration: *sudo service ntp restart*
-   Check if it works: *sudo ntpq -np*
-   More info:
    [here](https://help.ubuntu.com/community/UbuntuTime)

### Disabling the Multid NTP Client

This option instructs AVM's multid, through an additional parameter, not
to synchronize the time (requires multid restarts).

If chronyd is present in the firmware, multid is started in rc.net
without SNTP functionality. In addition, multid also disables this
function automatically when /var/run/chronyd.pid exists
([source](http://www.wehavemorefun.de/fritzbox/index.php/Multid#Aufruf)).

SNTP = Simple Network Time Protocol

openntpd automatically selects Remove chronyd.

### Troubleshooting

-   `dispatch_imsg in main: pipe closed`: `listen on` is used incorrectly
    in `openntpd.conf`.

### Alternative

The
["time"
service](http://en.wikipedia.org/wiki/Time_Protocol)
integrated in [inetd](inetd.html#user) can also be enabled. It can be
used, for example, with "rdate", which is already included in Freetz, or
also on the Dbox2.

### Further Links

-   [http://www.openntpd.org/](http://www.openntpd.org/)
-   [Article on
    OpenNtpd](http://www.zdnet.de/builder/program/0,39023551,39191851,00.htm)

