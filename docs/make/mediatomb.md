# mediatomb 0.12.1 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/mediatomb/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/mediatomb/)
  - Steward: -

**MediaTomb** is an open source (GPL) UPnP media server with a nice web
interface. It allows digital media to be streamed in the home network and
viewed or listened to on a wide range of UPnP-compatible devices, often
also labeled "DLNA".

A complete installation will fit into the Fritzbox filesystem only in a
few cases, unless many other things are omitted: the binary alone weighs
about 1.2 MB, plus roughly another 2.5 MB of dependencies (`libavcodec`
at a good 1.2 MB, `libsqlite3` at just under 700 kB, `libtag` at just
under 500 kB, `ffmpeg`, ...).

*MediaTomb* is configured through files (the
[UbuntuWiki MediaTomb
article](http://wiki.ubuntuusers.de/Mediatomb) describes this quite
well). Information about a web interface integrated into Freetz for this
purpose can be found, among other places, in
Ticket #1993

^(Maybe someone who has successfully put *MediaTomb* on their box would like to add notes on how, especially with regard to space requirements.)^

### Further Links

-   [MediaTomb Homepage](http://mediatomb.cc/)
-   [UbuntuWiki MediaTomb
  article](http://wiki.ubuntuusers.de/Mediatomb)
