# Downloader CGI
  - Package: [master/make/pkgs/downloader/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/downloader/)
  - Steward: -

The **Downloader-CGI** is described in detail in [this forum
thread](http://www.ip-phone-forum.de/showthread.php?t=134934). It helps
[save space in the Fritz!Box
filesystem](http://wiki.ip-phone-forum.de/software:ds-mod:development:platz_sparen)
by loading required packages from the network at runtime, so they do not
have to be installed permanently on the box. Downloader is mainly
interesting for boxes without a USB host and has been needed less and
less often recently.
The preparation script for External was extended with an automatic
preparation routine for Downloader. This prepares the actual offload
files as separate gz archives and also creates a file with the
Downloader-CGI configuration during the make procedure. The section is in
menuconfig under the External options.
External and Downloader differ in several ways:

1.  Downloader uses offloaded binaries as separate gz archives. External,
    in contrast, packs all files into one shared tar.bz2 archive.
2.  Downloader needs a Downloader-CGI with a service that, when the box
    starts, fetches the required files from an external HTTP or FTP server
    into the box's RAM. External has no such step. With External, the
    files are available immediately after the USB medium has been mounted.
3.  With Downloader, symlinks are created from flash to RAM while the
    firmware is being built. With External, these symlinks point to a
    previously agreed location on the USB medium.

The screenshots still date from the ds-mod era. Apart from the name
change to Freetz and a few cosmetic changes, however, not much has
changed since then.

**Main page:**

[![Downloader: Hauptseite](../screenshots/18_md.jpg)](../screenshots/18.jpg)

**Downloader logs while the box is booting:**

[![Downloader: Startlog](../screenshots/19_md.jpg)](../screenshots/19.jpg)

