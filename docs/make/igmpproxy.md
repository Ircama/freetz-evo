# IGMPproxy 0.4
  - Homepage: [https://github.com/pali/igmpproxy](https://github.com/pali/igmpproxy)
  - Changelog: [https://github.com/pali/igmpproxy/releases](https://github.com/pali/igmpproxy/releases)
  - Repository: [https://github.com/pali/igmpproxy/commits/master](https://github.com/pali/igmpproxy/commits/master)
  - Package: [master/make/pkgs/igmpproxy/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/igmpproxy/)
  - Steward: [@fda77](https://github.com/fda77)

**[igmpproxy](http://sourceforge.net/projects/igmpproxy/)**
is a simple multicast routing daemon used for multicast forwarding
between networks, for example for IPTV.

```
Usage: igmpproxy [-h] [-d] [-v [-v]] <configfile>

   -h   Display this help screen
   -d   Run in debug mode. Output all messages on stderr
   -v   Be verbose. Give twice to see even debug messages.
```

Configfile:

```
########################################################
#
#   Example configuration file for the IgmpProxy
#   --------------------------------------------
#
#   The configuration file must define one upstream
#   interface, and one or more downstream interfaces.
#
#   If multicast traffic originates outside the
#   upstream subnet, the "altnet" option can be
#   used in order to define legal multicast sources.
#   (Se example...)
#
#   The "quickleave" should be used to avoid saturation
#   of the upstream link. The option should only
#   be used if it's absolutely nessecary to
#   accurately imitate just one Client.
#
########################################################

##------------------------------------------------------
## Enable Quickleave mode (Sends Leave instantly)
##------------------------------------------------------
quickleave

##------------------------------------------------------
## Configuration for nas0 (Upstream Interface)
##------------------------------------------------------
phyint nas0 upstream  ratelimit 0  threshold 1
        altnet 10.1.12.0/24

##------------------------------------------------------
## Configuration for lan (Downstream Interface)
##------------------------------------------------------
phyint lan downstream  ratelimit 0  threshold 1

##------------------------------------------------------
## Configuration for Disabled Interfaces
##------------------------------------------------------
phyint dsl disabled
phyint lo disabled
```

For igmpproxy to run on the FritzBox, multid must be started with the
`-i` option (disable IGMP proxy). The interface names depend on the box
configuration and must be adjusted. In the example, "nas0", created by
[br2684ctrl](br2684ctl.html), is used as the upstream interface.

Currently, igmpproxy is available for Freetz only as a binary (0.1), so
there is no WebGUI for graphical settings yet.

### Further Links

-   [igmpproxy
    SourceForge](http://sourceforge.net/projects/igmpproxy/)
-   [IPPF thread: AONTV with the
    FritzBox](http://www.ip-phone-forum.de/showthread.php?t=208004&highlight=aontv)

