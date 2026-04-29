# SANE 1.0.27 - DEPRECATED
  - Package: [master/make/pkgs/sane-backends/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/sane-backends/)
  - Steward: -

### Description

This package makes it possible to operate scanners on the Fritz!Box. They
can then be used like printers from all computers in the local network.
It also makes it possible to use scanners directly from the Fritz!Box,
for example in scripts.

### Quick Start

### Installation and Configuration

-   make menuconfig
-   Make sure that `Show advanced options` is selected in the main menu
    and `Unstable` is selected under `Package selection`.
-   In the main menu, go to `Package selection` -> `Unstable` -> `SANE`
    and select `SANE`.
-   Recommendation: select `sane-find-scanner` and `scanimage`. These are
    not required for operation, but are helpful if scanning does not work
    in the next step. Once everything works, these two items can be
    deselected again to save storage space (~150 kB) and a new image can
    be created.
-   Select backend:
    -   Devices from Hewlett-Packard (HP): go one level higher, select
        HPLIP (HPLIP is currently available only in trunk), and then
        select `Printer Class` and `Printer Type` accordingly (help is
        available).
    -   For all other devices and very old HPs: determine the backend
        name from the [list of supported
        devices](http://www.sane-project.org/sane-mfgs.html) and select
        it.
-   Select `Inetd` under `Package selection` -> `Standard packages`
    (will be selected automatically in future versions)
-   Create image, flash, restart.

### Use from a PC under Linux/Windows

#### Linux

-   [XSane](http://www.xsane.org/) installieren
    (inkl. net-Backend)
-   `SANE_NET_HOSTS=fritz.box xsane` starten
    -   Tip: add a new line `fritz.box` to `/etc/sane.d/net.conf`; then
        typing only `xsane` is sufficient.

#### Windows

-   With [SaneTwain](http://sanetwain.ozuzo.net/), the scanner can be
    used from all Windows applications that support scanners through the
    TWAIN interface.
-   [XSane for
    Windows](http://www.xsane.org/xsane-win32.html)
    -   The language can be changed to German by setting the environment
        variable `LANG` to `de`. For example, the following in xsane.bat:

        ``` 
        @echo off
        set LANG=de
        c:sanebinxsane.exe
        ```

### Scanning Does Not Work

If scanning does not work as described in this guide:

-   Log in to the box and check there whether `sane-find-scanner` finds
    the device.
    -   If the recommendation to include sane-find-scanner and scanimage
        in the image was not followed: create and flash a new image with
        both tools.
-   If no scanner is found, the chances are poor.
-   If that works, use `scanimage -L` to check whether the scanner is
    listed. If this fails, something is wrong with the backend.
    -   Some backends require additional adjustments/settings, for
        example a firmware upload. Read the man page for the backend; the
        pages are also linked here:
        [http://www.sane-project.org/sane-mfgs.html](http://www.sane-project.org/sane-mfgs.html))
    -   The scanner may be supported, but the version of SANE or HPLIP in
        Freetz may be too old:
        [http://www.sane-project.org/sane-backends-1.0.19.html](http://www.sane-project.org/sane-backends-1.0.19.html)
        for Freetz 1.1.3; otherwise check under
        [http://www.sane-project.org/sane-supported-devices.html](http://www.sane-project.org/sane-supported-devices.html)
        or
        [http://hplipopensource.com/hplip-web/supported_devices/index.html](http://hplipopensource.com/hplip-web/supported_devices/index.html)
        and **compare versions**.
-   If the scanner was not listed, there is no point in continuing to try
    programs like `xsane`. Otherwise, continue reading under
    [Problems and Solutions](sane-backends.html#problems-and-solutions).

### Problems and Solutions

-   *Problem*: No scanner is found.
    *Solution*: Check network settings (does ping fritz.box work?); in
    the web interface under Services, check whether saned is running, and
    under Packages check the SANE settings (try resetting to defaults and
    make sure you are in the correct subnet); switch the scanner off and
    on again.
-   *Problem*: After scanning once, the scanner is no longer reachable.
    *Solution*: Make sure `Inetd` has been installed, and check in the
    web interface whether `inetd` is selected as the start type for saned
    (in future versions no other start type can be selected anymore and
    this problem no longer occurs).

### Limitations and Notes

-   By default, this package allows access for all computers in the LAN
    (192.168.178.0/24).
-   A scan process should not be aborted, as this can cause the scanner
    to freeze.
-   In addition to pure scanners, multifunction devices with scanners and
    a few cameras are also supported.
-   It should be possible to connect several scanners at the same time
    (not tested).
-   Not all SANE backends are included (for those interested:
    [[source:trunk/make/sane-backends/config-update.pl#L134](/browser/trunk/make/sane-backends/config-update.pl#L134){.source}[​](/export/HEAD/trunk/make/sane-backends/config-update.pl#L134 "Download"){.trac-rawlink})
-   Despite its name, saned is not a daemon.
-   saned is not needed for scanning with scanimage on the box.
-   scanimage is not needed for scanning via saned.

### Notes on Specific Devices

#### AGFA SnapScan e20

-   Obtain firmware file, for example from a Windows installation -
    snape20.bin
-   copy it into the folder "`root/usr/share`"
-   adjust the files "`snapscan.conf`" and "`snapscan.conf.in`" from the
    folder "`source/sane-backends-1.0.19/backend`":

```
#------------------------------ General -----------------------------------

# Change to the fully qualified filename of your firmware file, if
# firmware upload is needed by the scanner
firmware /usr/share/snape20.bin

# If not automatically found you may manually specify a device name.
```

-   create freetz image
-   and the scanner can then be used, for example, with xsane

#### Mustek BearPaw 1200 TA

-   Obtain firmware file - A1fw.usb -
    [http://www.meier-geinitz.de/sane/gt68xx-backend/](http://www.meier-geinitz.de/sane/gt68xx-backend/)
-   Enter in the freetz directory:

    ``` 
    mkdir -p make/sane-backends/files/root/usr/share/sane/gt68xx
    cp <path to A1fw.usb> make/sane-backends/files/root/usr/share/sane/gt68xx
    ```

-   create freetz image

#### HP Devices That Require a Plugin

The following HP devices require a plugin for scanning that is available
only for x86 and x86_64, and according to current knowledge they cannot
be operated as scanners on the Fritz!Box (see also
[forum](http://www.ip-phone-forum.de/showthread.php?t=108479&page=19#379)):

-   HP Color LaserJet CM1015 Multifunction Printer
-   HP Color LaserJet CM1017 Multifunction Printer
-   HP Color LaserJet CM1312 Multifunction Printer
-   HP Color LaserJet CM1312nfi Multifunction Printer
-   HP Color LaserJet CM2320 Multifuntion Printer
-   HP Color LaserJet CM2320fxi Multifunction Printer
-   HP Color LaserJet CM2320n Multifunction Printer
-   HP Color LaserJet CM2320nf Multifunction Printer
-   HP LaserJet M1005 Multifunction Printer
-   HP LaserJet M1120 Multifunction Printer
-   HP LaserJet M1120n Multifunction Printer
-   HP LaserJet M1319f Multifunction Printer
-   HP LaserJet M1522 Multifunction Printer
-   HP LaserJet M1522n Multifunction Printer
-   HP LaserJet M1522nf Multifunction Printer
-   HP LaserJet M2727 Multifunction Printer
-   HP LaserJet M2727nf Multifunction Printer
-   HP LaserJet M2727nfs Multifunction Printer

In general, all devices for which models.dat from HPLIP lists scan-type
3, 4, or 5 are affected.

### Further Links

-   [IPPF-Thread](http://www.ip-phone-forum.de/showthread.php?t=108479)
    about the creation of this Freetz package, with relevant notes
-   [SANE-Homepage](http://www.sane-project.org/)
-   [Devices supported by
    SANE](http://www.sane-project.org/sane-mfgs.html)
-   [XSane](http://www.xsane.org/)
-   [HPLIP](http://hplipopensource.com/)
-   [Devices supported by
    HPLIP](http://hplipopensource.com/hplip-web/supported_devices/index.html)

