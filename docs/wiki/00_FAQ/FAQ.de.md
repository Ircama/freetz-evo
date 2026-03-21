# FAQ

This page answers frequently asked questions about Freetz.

Note: This document is still being refined. Some sections may remain more detailed in older historical versions.


### Project Name and History

### What is Freetz?

> *Freetz* is a toolbox for developers and experienced users to build a
> modified firmware based on the original firmware for the
> DSL/LAN/WLAN/VoIP-Routers [AVM
> Fritz!Box](http://www.avm.de/de/Produkte/FRITZBox/index.html)
> and [T-Com
> Speedport](http://www.t-home.de/is-bin/INTERSHOP.enfinity/WFS/EKI-PK-Site/de_DE/-/EUR/ViewFAQTheme-Download;?ProductThemeId=theme-1000&selaction=themen&FaqId=theme-28565177&pageNr=0&bound=2&itemLocator=downloads&headerSelection=2&SelectedTheme=theme-28565177&SelectedTheme=theme-2001628)
> (identical hardware) and to transfer this firmware to the device.
> There are many extension packages available, along with options to
> remove unwanted functionality from the original firmware.

### Where does the name Freetz come from?

> It is a contraction of the word "free" and the name "Fritz",
> intended to mirror the name of the devices manufactured by
> [AVM](http://www.avm.de). With this, we want to
> symbolize that *Freetz* is free software. In order to avoid
> intellectual property problems with AVM, whose registered trademark
> "Fritz!" (with exclamation mark) we explicitly acknowledge, we have
> chosen this deliberately different spelling. The idea for the name
> came from Alexander Kriegisch (kriegaex), who decided together with
> Oliver Metz (olistudent) what the project should be called when the
> version-managed source code repository would be opened to the public.
> From the (in our opinion daft-sounding) alliteration "Free Fritz" we
> got "Freetz". ("OpenFritz" was also considered, but we didn't
> want to mimic [OpenWrt](http://openwrt.org).) We
> don't claim that the name is fantastic, but it is short and hopefully
> easy to remember. :-)

### How should I pronounce Freetz?

> Like the English word "free" with a German-sounding "tz" on the
> end, something like "freets".

### How did Freetz start?

> There are many predecessors to *Freetz*. A few years ago, Daniel
> Eiband (danisahne) started the *Danisahne-Mod* ( *DS-Mod* ) based on
> the previous work and cooperation of other creative people (Erik
> Andersen, Christian Volkmann, Andreas Bühmann, Enrik Berkhan and
> others). As with *Freetz*, this allowed and still allows modified firmware
> to be created, but only for older firmware versions with Linux kernel
> 2.4. Since some routers still have firmwares based on the Linux 2.4
> kernel, the version
> [ds-0.2.9-p8](http://www.ip-phone-forum.de/showthread.php?t=135253)
> is still the current version for some hardware. For the majority of
> current hardware, the immediate predecessor of *Freetz* is, however,
> *ds26* (latest version
> [ds26-15.2](http://www.ip-phone-forum.de/showthread.php?t=144646)
>), created by Oliver Metz, which is only suitable for firmware using
> Linux kernel 2.6. The same applies to *Freetz*, as *Freetz* is
> currently nothing other than the current development version of *ds26*
> with a new name. In many files you will therefore still find the name
> *DS-Mod*, which will gradually be replaced with the new name *Freetz*.

### Why change the name when DS-Mod has already become well-known?

> There are multiple reasons. For one, Daniel has not been actively
> involved in the development of *ds26* for well over a year. For
> another, he has already started a new project at
> [SourceForge](http://sourceforge.net) to develop
> a new *DS-Mod* from scratch - which we unofficially call *DS-Mod NG
> (Next Generation)* - for which the source code repository is publicly
> available on his [project
> website](http://ds-mod.sourceforge.net). We don't wish to
> take Daniel's project name from him, or to compete with him, but
> actually hope that he will eventually have more time for his project
> and that we will be able to combine both versions to have the
> strengths of both of them in one product. However, at this point in
> time, the projects have split significantly; *DS-Mod NG* has a very
> clean structure, but is not yet finished, whereas *Freetz* (previously
> *ds26*) is already widely used and is gradually being refactored
> during the process of development. Where *DS-Mod* was talked about in
> recent press coverage (e.g.
> [PC-Welt](http://www.pcwelt.de/start/dsl_voip/dsl/praxis/98946/index3.html)
>), *Freetz* alias *ds26* was meant.

### Why is so much of Freetz and the development in German?

> AVM is a German company, and their hardware is mainly sold on the
> German market, where it is very popular and generally the
> German-language (and German telecoms-system) versions of their
> products are the first to be released. It is therefore not surprising
> that the project started in Germany and most of the developers are
> German. There are some current ideas of how to better integrate
> internationalization support, and although most development
> discussions take place in German, contributions in English are most
> welcome (and will usually be answered in English).

### Motivation

### Why change the firmware?

> It is possible to edit some special files (character devices) under
> /var/flash where the contents still exist after reboot, but this is
> not true for the rest of the filesystem. The content of these
> character devices is located in its own rather tiny flash partition.
> Most data is stored on a read-only SquashFS filesystem which can only
> be modified during a firmware update, using a SquashFS filesystem
> image. To permanently include (larger) files into the firmware, they
> must be put into the SquashFS image, which is implemented in Freetz.

### Distribution

### Can I get a finished binary of Freetz?

> The short answer is no, and this is never likely to be possible.
> *Freetz* works by taking the original firmware and applying patches to
> it. Since the original firmware contains software that is non-free,
> as well as some which is free, that means we are not able to
> distribute finished binary versions. Also, given the number of
> permutations of modules and hardware then it would be impossible to
> meet all needs with a limited number of binaries and so it is actually
> of advantage to have users build their own firmware, tailored to their
> individual needs.

### How can I get Freetz?

> See the Getting Started page for how to check
> out the source code and get started with *Freetz*. Note that this
> requires a working Linux installation (a Live-CD or Virtual Machine
> version will do if you do not want to fully install Linux on your
> computer). Please make sure that you have basic Linux skills before
> requesting help as this will make your, and our, lives easier.

### Which box types and firmware versions are currently supported?

>  *  [Trunk](../../FIRMWARES)

### Development

### When will version xy be released?

> Generally speaking: "It's done when it's done." The developers are
> working in their spare time, and new releases are provided when the
> planned features are complete and release-critical bugs are fixed.

> Still, a rough plan for new releases does exist: 3-4 months after a
> stable release we declare a "feature freeze" for the following
> release. From that time on, only bugs are being fixed. The
> feature-freeze dates are announced in the [roadmap](/roadmap). After
> the feature freeze you can expect the final release in
> about 1 to 1.5 months. Between stable feature releases, there can
> be maintenance releases provided to support newer firmware
> versions by AVM or to deliver bug fixes.

### Trunk, Branches, and Tags

> The trunk is the current development tree.
> A branch is a tree separated from the trunk at a specific
> time (e.g. Changeset r2759).
> All release versions are tagged

> To check out the current development version:
>
> ```
> git clone https://github.com/Freetz-NG/freetz-ng ~/freetz-ng
> ```

### When will feature XY be implemented?

> The fastest way is to present a working solution. We take notice of
> every reasonable feature request. Due to the developers designing
> Freetz in their spare time, you may need to be patient.

### I like Freetz and want to support development

> It is possible to donate money to the development team using the
> PayPal donation button at the bottom right-hand corner. Further, a
> specific hardware variation will of course be better supported when
> the development team has some test hardware. Currently we would very
> much benefit from some 7270s (who wouldn't?!). There is a thread on
> the topic of donations at
> [IPPF](http://www.ip-phone-forum.de/showpost.php?p=959253&postcount=1)
> .

### Pre-Configuration (menuconfig)

### Do I have the 8MB (v1) or 16MB (v2) version of the FRITZ!Box 7270?

1. Read the support file at
    [http://fritz.box/html/support.html](http://fritz.box/html/support.html).
2. The file should contain one of the following entries:

-   8MB: **flashsize 0x00800000**
-   16MB: **flashsize 0x01000000**

0x00800000 hex = 8,388,608 decimal = 8,192 KB = 8 MB\
0x01000000 hex = 16,777,216 decimal = 16,384 KB = 16 MB\

More details are described
[\[here\]](http://www.ip-phone-forum.de/showpost.php?p=1124950&postcount=2).

### What are indicators for a FRITZ!Box 7270v3?

-   Firmware version. Firmware for the 7270v3 starts with `74.xx.xx`.
-   Serial number.

### Which packages should be built into a Freetz image?

> We recommend Dropbear to have SSH access, as well
> as dnsmasq as DHCP server replacement.

### What does "binary only" mean?

> Packages tagged with "binary only" do not supply any web frontend,
> init script or anything similar. They provide only the binaries
> themselves, which means you have to take care of the configuration,
> initialization etc. yourself. (Note: Other than the name (maybe)
> suggests, these packages are - along with every other package in
> Freetz - built from source.)

### Image Build (make/build)

### Meaning of specific make targets

A: Make targets influence the build process and firmware creation.
Most of the following information was taken from
[this
thread](http://www.ip-phone-forum.de/showthread.php?p=1185868)
originally.

**1. Clean-Up:**

-   *make clean\
    *...

<!-- -->

-   *make \<package\>-clean*:\
    Basically, this calls the clean-target of the original package's
    Makefile. It will delete all generated files (first and foremost the
    object-files, libraries and executables) but leaves its
    configuration intact.
    A following *make* command doesn't apply changed patches, but
    creates only the above-named object-files, libraries and executables
    from the source-files (compiling).
    Example: *make mc-clean* would clean the "Midnight Commander"
    package (mc).

<!-- -->

-   *make \<package\>-dirclean*:\
    Deletes the whole directory of the package. A following *make*
    command will extract the files, apply the patches, configure and
    compile the package.
    Only the last stage (compilation) would take place after a *make
    \<package\>-clean* command (as described above).

<!-- -->

-   *make dirclean*:\
    As the name implies, this performs a "directory-cleanup". The
    directories */packages, /source, /build, /toolchain/build,
    toolchain/target* (and some other stuff(?)will be deleted, so that a
    following *make* command must build everything new. This is
    recommended if changes caused by *svn up* will result in a firmware
    which is not working as expected. Alternatively, if you know exactly
    which package(s) are causing them problem, you can clean these
    package files via *make \<package\>-dirclean* individually (see
    above).
    Note that, after a *make dirclean*, the build process to create the
    firmware will take more time than it did before because everything
    must be rebuilt from scratch.

<!-- -->

-   *make tools-distclean*:\
    deletes the tools (busybox, lzma, squashfs, others)

<!-- -->

-   *make distclean*:\
    In addition to *make dirclean*, this also deletes the download
    folder and the tools.

<!-- -->

-   *make config-clean-deps*:\
    If some packages were deselected via *make menuconfig*, maybe some
    shared libraries are still selected but are not needed anymore by
    any active package (that happens because *menuconfig* cannot
    recognize this by itself). Such libraries can manually be disabled
    under 'Advanced Options'→'Shared Libraries' - libaries; the ones
    that are still in use cannot be deselected. Alternatively, you can
    also do this automatically via *make config-clean-deps*.
    Furthermore, Busybox applets manually selected in *make menuconfig*
    will be reset (\*not\* those modified via *make
    busybox-menuconfig*!).

<!-- -->

-   *make config-clean-deps-keep-busybox*:\
    Like *make config-clean-deps*, but does not reset Busybox applets.

<!-- -->

-   *make kernel-dirclean*:\
    deletes the current source-tree of the kernel, to build it
    completely new from clean sources. (important if something has
    changed at the kernel patches)

<!-- -->

-   *make kernel-clean*:\
    analogue to *make \<package\>-clean*

<!-- -->

-   *make kernel-toolchain-dirclean*:\
    deletes the kernel compiler

<!-- -->

-   *make target-toolchain-dirclean*:\
    deletes the compiler for the uClibc and the binaries (executables)

**2. Preparations:**

-   *make world*:\
    Prerequisite is a toolchain (see 'Cross-Compiler / Create Toolchain'.
    If problems with non-existing directories occur, it's possible that
    *make world* can fix this. But normally this should not be
    necessary.

<!-- -->

-   *make kernel-toolchain*:\
    compiles the kernel and also for the target (FRITZ!Box)\
    Due to historical reasons the label was kept as *kernel-toolchain*,
    although, as mentioned, not only the kernel will be built but also
    the packages (see below).

<!-- -->

-   *make target-toolchain*:\
    Compiles the packages for the target (FRITZ!Box).

<!-- -->

-   *make kernel-menuconfig*:\
    The configuration of the kernel will be saved after finishing under
    ./make/linux/Config.\<kernel-ref\>.

<!-- -->

-   *make kernel-precompiled*:\
    Build the kernel and the kernel modules.

<!-- -->

-   *make menuconfig*
    (Source): To
    configure Freetz it makes use of *conf/mconf*, which some or other
    already knows from the linux kernel configuration. The
    [ncurses](http://en.wikipedia.org/wiki/Ncurses)
    variant *mconf* can be called with the command *make menuconfig*.
    [By the way]{.underline}:\
    A help for each item can be accessed directly in *menuconfig* by
    pressing "?".
    After entering "/" you can search across all leaves for any
    strings - really practical.

### Building another firmware language

The firmware language/version should match your box type, else your box
will go into a reboot loop.

Check the advanced option *Enforce urlader environment* and put **avm**
in *Patches \> Enforce firmware_version variable* to build
[German]{.underline} firmware for an [international]{.underline} box. If
you want to do this (or the other way around with **avme** for
[English]{.underline} firmware on a [non-international]{.underline}
box), read about recovery and
have a working/recovery image ready.

### Problems during building

If you encounter problems during the build process, go through this list
first:

#### You must have either have gettext support in your C library, or use the GNU gettext library.

> There is a wrong value in config.cache. Delete the file by typing:
> "rm make/config.cache" or "rm source/target-mipsel_uClibc-
> *0.X.XX* /config.cache"

#### ERROR: The program/library/header xy was not found...

> If the build process was interrupted by this message, some necessary
> packages for the build system are missing. Please install them and
> restart the build process.

#### WARNING: The program/library/header xy was not found...

> If the build process was interrupted by this message, maybe some
> packages providing the needed library are missing. This can be caused
> by selecting some options or packages in menuconfig. Please install
> the needed libraries by installing the packages and restart the build
> process.

#### No such file \`FRITZ.Box_xxxxxxxxx.aa.bb.cc.image'

> This happens every time AVM releases a new firmware version. Normally
> only the newest file is available on the AVM FTP server. Freetz can
> only support the version that's current at the release date. Due to
> license restrictions, we cannot provide these images. Possible
> solutions (prioritized by difficulty):

-   for everyone: at
    [Firmware-Collector-Thread](http://www.ip-phone-forum.de/showthread.php?t=119856)
    you can ask for an older firmware version (NO beta firmwares). The
    image must be downloaded and copied to the directory 'dl/fw'.
-   for beginners: Use the `stable` Branch from the SVN repository. If
    possible, update to a newer version which supports the latest AVM
    firmware versions (or wait for an upcoming Freetz release).
-   for novices: Use the developing tree (`trunk`) from the SVN
    repository. The latest firmware versions are supported here.
-   for experts: At 'make menuconfig' under *Advanced
    Options ⇒ Override firmware source* change the name of the file to
    download and use.

Please use the last 2 possibilities at your own risk. If it's just a
"bugfix release" (like the update from .57 to .59) it should work
without errors. However, if major changes were done by AVM at the latest
firmware release, use it carefully!!

#### Please copy the following file into the 'dl/fw' sub-directory manually: fritz_box_aa_bb_cc-ddddd.image

> The beta firmwares (Labor-Firmware) cannot be downloaded from the
> AVM-FTP-Server. Please download them manually from the
> [AVM-Labor-Site](http://www.avm.de/Labor) . You
> must agree the license terms to get the file. After finishing
> download, put all files into the 'dl/fw' directory. Please also
> consider the headpoint before.

#### ./ln: cannot execute binary file

> The current working directory '.' is within the path (variable
> PATH). To make a successfully build, the directory must be removed.

#### Filesystem image too big

> The firmware image doesn't fit into the flash memory of the selected
> box.

-   With some boxes, this can happen if none of the packages are
    selected, because the basic Freetz components use some space and the
    AVM images are just under the maximum flash size. In this case,
    it's necessary to use one or more Remove-Patches under the
    'Patches'-Section to remove unused components of the original
    firmware.
-   If a lot packages are selected, reconsider if all packages are
    really necessary, or try via
    external/[Downloader](http://www.ip-phone-forum.de/showthread.php?t=134934)/USBRoot/NFSRoot
    to externalize some of the components to reduce the image size.
    Further information is available at
    [IPPF](http://www.ip-phone-forum.de/showthread.php?t=136974)
    and in the
    [WIKI](http://wiki.ip-phone-forum.de/software:ds-mod:development:platz_sparen)
-   With boxes with an USB-Host (e.g. 7170,7270) you can externalize
    some packages on an USB device (e.g. USB Stick, USB hard disk). The
    externalize-process is done at the end of the build process via the
    external-script. At
    menuconfig, there is an option to do the externalizing. Only
    predefined parts of packages are being externalized to a USB-Device,
    as opposed to using USB-Root which will move the entire file system
    onto the USB drive.
-   If a package was deselected, maybe some shared libraries are still
    enabled but are not needed anymore. (menuconfig cannot recognize
    this by itself). These libraries can manually be deselected under
    'Advanced Options'→'Shared Libraries' - libraries currently in
    use cannot be deselected. Another option is to do this via the
    command *make config-clean-deps* or *make
    config-clean-deps-keep-busybox*, respectively.

#### WARNING: Not enough free flash space for answering machine!

> The image is small enough to fit on flash memory, but you have not
> enough free space left for the answering machine, or non space left.
> The firmware should work in spite of this message, but to ensure a
> fully functional answering machine or fax service, you should use an
> FAT-formatted USB-Stick to use this space for the answering machine,
> fax service and other services.

> Background Information: Since a few firmware versions, AVM tries to
> use the remaining bytes in the Flash to create an jffs2-Partition. In
> this partition all data for e.g. the answering machine, fax service
> and so on are stored. On older boxes (e.g. 7170) the jffs2-Partition
> cannot be created as space howsoever is very limited. Please see this
> message as an warning. More informations at the
> [IPPF-Thread](http://www.ip-phone-forum.de/showthread.php?t=186208)
> . In FREETZ available since revision
> Changeset r3049
> .

### The problem still occurs. What now?

> At first go into the 'Advanced Options' of menuconfig, change the
> 'Verbosity Level' to 2 and execute make again. After that go to the
> [IPPF
> Forum](http://www.ip-phone-forum.de/forumdisplay.php?f=525)
> and search for the error message or for an existing thread. If nothing
> could be found, create a new thread to get help with the given error
> message (please post it inside Code-Tags), the file .config (your
> configuration as attachment) and the used version or SVN
> branch/-revision.

### Flashing a compiled image

### Problems after (successful) Flashing

### Settings are not available at current security level

> There are several security levels. The level can be changed using the
> following commands:
>
> ```
>    echo x > /tmp/flash/security ( after r3318: echo x > /tmp/flash/mod/security)
>    modsave
>
>  * with x being one of the following values:
>  * 0 : no restrictions
>  * 1 : only configuration files without shell commands (shell scripts) can be modified
>  * 2 : no configuration files can be modified
> ```

### What is the default password for Freetz?

The default password for Freetz (both for console and web login) is
"freetz". The login name for console is "root", and for the web
interface it is "admin". When you first log in using Telnet or SSH, you
have to change your password.

### The Info LED blinks twice periodically

See [this
thread](http://www.ip-phone-forum.de/showthread.php?t=216590).

### Configuration

### Where is the full configuration stored on the FRITZ!Box?

> The full configuration on the FRITZ!Box can be found under `/tmp/flash`.
> This is important if you build a Freetz firmware, because the
> configuration is not located in the static firmware part of the image.
> Files located under `/tmp/flash` are not edited during firmware
> updates, so configuration files are preserved.
> Always execute `modsave` after making changes to configuration files
> under `/tmp/flash` so they are saved in flash.

### Configuration not available at the current security level!

> There are different security levels. Depending on the selected level,
> not all configuration files are editable.
>
> ```
> echo x > /tmp/flash/security (since r3318: echo x > /tmp/flash/mod/security)
> modsave
> # with x being one of the following values:
> # 0 : no restrictions
> # 1 : only configuration files without shell commands (shell scripts) can be modified
> # 2 : no configuration files can be modified
> ```

* **ATTENTION:**
Between x and \> there must be at least a single blank space. If there
isn't, the file will be empty. (echo will redirect to stdout. The
output would be empty then. Alternatively, you could also write
"x"\>security.

This must be done after installing the new firmware on the Box via
Telnet or SSH (not possible over the Rudi-Shell, because it also
requires security level "0").

### How can I disable the password for the Freetz website?

> Execute the following command on the terminal:
>
> ```
> touch /tmp/flash/webcfg_conf
> chmod +x /tmp/flash/webcfg_conf
> modsave flash
> /etc/init.d/rc.webcfg restart
> ```
>
> Background: The script /tmp/flash/webcfg_conf will be preferred
> compared to /etc/default.webcfg/webcfg_conf to create the
> configuration file. An empty script /tmp/flash/webcfg_conf will
> create an empty configuration file without a password.

> * For Freetz-1.1.x, replace `/tmp/flash/webcfg_conf` with `/tmp/flash/httpd_conf`.

### How can I change the password for the Freetz website?

> This can be done directly via the [web interface](http://fritz.box:81/cgi-bin/passwd.cgi):
> `http://fritz.box:81/cgi-bin/passwd.cgi`

### How can I reset the password for the Freetz website in case I've lost it but still have access via Telnet/SSH?

> At first, stop the Freetz-Webif:
>
> ```
> /etc/init.d/rc.webcfg stop
> ```
>
> Then use vi to open the file mod.cfg and edit the line that begins
> with "export MOD_HTTPD_PASSWD" as follows:
>
> ```
> vi /var/mod/etc/conf/mod.cfg
> ```
>
> ```
> export MOD_HTTPD_PASSWD='$1$$zO6d3zi9DefdWLMB.OHaO.'
> ```
>
> Now start the Freetz-Web interface:
>
> ```
> /etc/init.d/rc.webcfg start
> ```
>
> Now you can log in to the Web interface with the password "freetz".

> Please note that this change will **NOT** persist across reboots.
> So after a reboot, you still have the old unknown password.
> Therefore, you should change the password of the Box in the
> Freetz menu under *Settings* before you reboot your FRITZ!Box.

### How can I change the root password?

> Execute the following commands on the terminal:
>
> ```
> passwd
> modusers save
> modsave flash
> ```
>
> After entering 'passwd' you must type in the password. While typing,
> the password will 'not' be shown. Too simple passwords will not be
> accepted.

### Problems during operation

### /var/flash/freetz is too big

> The default limit set by Freetz for the maximum size of the
> configuration was exceeded. This limit is a protection to prevent an
> unintended full TFFS. This limit can be increased, but you should keep
> an eye on the current fill level:
>
> ```
> modconf set mod MOD_LIMIT=<bytes>
> modconf save mod
> modsave flash
> ```

* As of Changeset r5706, the setting MOD_LIMIT is obsolete.

### No FTP Access After Freetz

> This is a problem which occurs especially in Freetz 1.1.x. More
> details and solution can be found in the
> howto.

### Removing Freetz and Other Modifications

### Miscellaneous

### How can I use a custom DNS server for all connected PCs and the FRITZ!Box?

AVM does not always allow changing the default DNS servers used by the
box through the WebUI.

> Possible Solutions:

-   dnsmasq: Installation of your own DNS server on the FRITZ!Box with the
    package dnsmasq. This is a general
    possibility that works on every box. This requires a
    modified firmware image. With an edited
    version of /etc/resolv.conf (if using the trunk version, this is
    possible via the GUI under "Settings"→"Freetz: resolv.conf") you
    can add a DNS server: "nameserver 208.67.220.220" (example with
    the OpenDNS server)
-   without dnsmasq: At some boxes, e.g. 7170(FV 29.04.76) it's
    possible to edit the central config file of AVM. With the command
    "nvi /var/flash/ar7.cfg" all entries of "overwrite_dns1 =
    xxx.xxx.xxx.xxx" and "overwrite_dns2 = xxx.xxx.xxx.xxx" must be
    edited. It is recommended only for users with basic knowledge of
    nvi and Telnet/SSH. Here, the
    multid from AVM is running as DNS server. At the resolv.conf a
    loopback entry "nameserver 127.0.0.1" exists. This allows
    Linux standard applications to resolve names on the FRITZ!Box via
    multid.
-   Editing /etc/resolv.conf: If it is only about changing the current
    DNS used by the FRITZ!Box, editing /etc/resolv.conf as described
    above at dnsmasq also works. This is only affecting the name
    resolution of the box; connected clients are still using the
    standard DNS.

### How can I create character devices?

Freetz also uses a *[character
device](http://en.wikipedia.org/wiki/Character_device#Character_devices)*,
which can save files persistently with help of a Tiny Flash Filesystem
(TFFS) in the Flash, to save the configuration. Prerequisite is a minor
number, which is not used by any other character device under
`/var/flash/` (Freetz uses the minor 0x3c), the major number can be read
from `/proc/devices`:

```
mknod /var/flash/<name-of-file> c <major> <minor>
```

Because this character device is created in a
[ramdisk](http://de.wikipedia.org/wiki/RAM-Disk)
under `/var/`, this command must be executed every time during a
restart. The content is preserved.
* To edit such character devices, **never** use `vi`. Use the wrapper script `nvi` instead.

* **ATTENTION:**
    The flash partition of TFFS is very small and often cannot contain
    files \> 10-30 KB (depending on the size of other files).

The current fill level can be shown like this:

```

    echo 'cleanup' > /proc/tffs

    echo 'info' > /proc/tffs

    cat /proc/tffs | grep '^fill='
```

### Which network cable is necessary for recovery?

RJ45 standard network cable, no crossover

### How old is my FRITZ!Box?

The first four characters of the box' serial number describe its age:\

Example: **W484**-xxx-xx-xxx-xxx ⇒ **Thursday, 27.11.2008**\

U = 2006\
V = 2007\
W = 2008\
X = 2009\
A = 2010\

W451 = calendar week 45 and the first day of that week = Monday\
W462 = calendar week 46 and the second day of that week = Tuesday\
W473 = calendar week 47 and the third day of that week = Wednesday\
**W484 = calendar week 48 and the fourth day of that week = Thursday**\
W495 = calendar week 49 the fifth day of that week = Friday\



### How much RAM does my FRITZ!Box contain?

For the second xxxx-**XXX**-xxx-xxx currently, the following codes are
known to occur:\

Example: W484-**305**-xx-xxx-xxx ⇒ **FRITZ!Box with 16MB and 1und1
branding**\

293 - HWRev 122 (8MB/7270_V1) - AVM branding\
294 - HWRev 122 (8MB/7270_V1) - 1und1 branding\
304 - HWRev 139 (16MB/7270_V2) - AVM branding\
**305 - HWRev 139 (16MB/7270_V2) - 1und1 branding**\
xxx - HWRev 145 (16MB/7270_V3) - ??? branding - 7270_V3\
307 - HWRev 139 (16MB/7270_V2) - AVME branding International Version?\
310 - HWRev 139 (16MB/7270_V2) - AVME branding A-/CH-Version?\


