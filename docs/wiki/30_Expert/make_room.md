# Saving Space in the FRITZ!Box Filesystem

### Foreword and Motivation

Every modder who has ever seen corresponding `fwmod` error messages while
assembling firmware (FW), and then had to start thinking about which
Freetz packages to leave out, knows that space in the FRITZ!Box
filesystem is limited, especially on still common "small" routers such
as the 5050 or 7050. This problem is discussed, for example, in the IPPF
thread [7050 too tight: manually move DS-Mod parts to an external
drive](http://www.ip-phone-forum.de/showthread.php?t=132936), and also
elsewhere.

Without presenting a finished "slimming tool" here, I would simply like
to summarize, for clarity, the means and methods that currently come to
mind if I had to save space on my box. The goal is to provide help for
self-help and a few ideas so everyone can pursue the paths that seem most
promising to them. This small overview claims neither completeness nor
absolute correctness or practical proof. I currently have no space
problems with my 7170, because I am also not the type who wants to run
"everything" on the box. Incidentally, that is already the first and one
of the most effective ways to save space: not exaggerated, but
appropriate modesty and concentration on what is necessary.

### Inventory: Where Are the Space Hogs?

Before we think about where we can save, we should first get an overview
of where the most space is used. In the second step, we distinguish
between necessary and unnecessary space hogs, called SHs below. Finally,
we proceed according to the
[Pareto principle](http://de.wikipedia.org/wiki/Pareto-Verteilung#Pareto-Prinzip)
to achieve the greatest possible effect with manageable effort.

### Step 1: Examine the Original Firmware

Which files consume the most space in the original firmware? The easiest
way to check this after a `make` is to look at the directory where the
unpacked firmware files are stored: `build/original/filesystem`. With the
following command we search the directory for files (`find -type f`) and
pass all those files to `ls`, causing it to sort them by size in
descending order. As an example, here is AVM firmware 29.04.29 for the
7170. For clarity, I omit unimportant columns from the result list.

```
	$ cd build/original/filesystem
	$ find . -type f | xargs ls -lSR | more

	1291372 lib/libcrypto.so.0.9.8
	 858208 lib/modules/2.6.13.1-ohio/kernel/drivers/isdn/isdn_fon4/zzz/isdn_fbox.ko
	 730844 lib/modules/2.6.13.1-ohio/kernel/drivers/dsld/kdsldmod.ko
	 551944 usr/bin/telefon
	 473772 lib/modules/2.6.13.1-ohio/kernel/drivers/net/wireless/avm_wlan/wlan/tiap.ko
	 425652 lib/libuClibc-0.9.28.so
	 416632 bin/busybox
	 314836 lib/libavmcsock.so.2.0.0
	 303784 lib/modules/microvoip-dsl.bin
	 283853 lib/modules/microvoip_isdn_top.bit1
	 274704 usr/bin/ctlmgr
	 274352 lib/libsiplib.so.2.0.0
	 259052 lib/libssl.so.0.9.8
	 252344 usr/share/ctlmgr/libtr069.so
	 234684 usr/share/ctlmgr/libfon.so
	 212468 lib/modules/microvoip_isdn_top.bit
	 212432 sbin/dsld
	 202684 lib/libmscodex.so.2.0.0
	 167180 sbin/fsck.ext2
	 163360 sbin/multid
	 158332 lib/modules/2.6.13.1-ohio/kernel/drivers/usb/core/usbcore.ko
	 154224 usr/bin/wpa_authenticator
	 142624 lib/modules/2.6.13.1-ohio/kernel/drivers/atm/avm_atm/tiatm.ko
	 142104 lib/libosipparser2.so.4.0.0
	 134308 lib/modules/2.6.13.1-ohio/kernel/drivers/scsi/scsi_mod.ko
	 132296 lib/libar7cfg.so.1.0.0
	 117056 lib/libm-0.9.28.so
	 116804 bin/voipd
	 106192 lib/modules/fw_dcrhp_1150_ap.bin
	 102712 usr/lib/libext2fs.so.2.4
	 102472 sbin/fdisk
```

Now you can start thinking about what might be dispensable. Leaving out
Busybox or the DSL daemon makes no sense; it makes more sense to omit
unnecessary applets from Busybox. Some may consider not needing the WLAN
components and instead wanting more space for OpenVPN. That is only an
example, independent of whether the box starts cleanly without the WLAN
binaries. Comment: the WLAN module, `tiap.ko`, can be removed without
problems. If files are omitted, the corresponding services should be
disabled or, if necessary, things should be commented out in the relevant
startup scripts for safety. With other programs, the decision is easier:
normally `fdisk` is not needed unless you want to create a filesystem
with `mkfs.ext2`. So a little space can be saved by leaving it out,
perhaps the decisive kilobytes that let another extension fit onto the
box. For other candidates such as `libtr069`, the small boxes already
have switches in the Freetz menu configuration to omit them. In general,
inspect the startup files under `/etc/init.d` to find out whether and
when a particular file is loaded. For required libraries, the analysis is
somewhat more difficult, but also possible.

### Step 2: Examine the Mod Firmware

We now do the same thing we just did for the original firmware with the
mod firmware configured according to our wishes. Even if it perhaps could
not be built successfully because, for example, there was not enough
space, we can still see the generated filesystem under
`build/modified/filesystem`. The following example is from my 7170 with
mod version ds-0.2.9_26-14.2 and, roughly speaking, these enabled
options and extensions: 1&1 branding, no help texts and assistants,
original kernel, Bftp, Callmonitor, Cifsmount, Dropbear (server only),
MC, Mini_fo, Samba, Screen, Syslogd-CGI, WoL-CGI, Lua, Matrixtunnel. It
looks like this:

```
	$ cd build/modified/filesystem
	$ find . -type f | xargs ls -lSR | more

	1291372 lib/libcrypto.so.0.9.8
	 913456 usr/sbin/smbd
	 858208 lib/modules/2.6.13.1-ohio/kernel/drivers/isdn/isdn_fon4/zzz/isdn_fbox.ko
	 779956 usr/bin/mc.bin
	 730844 lib/modules/2.6.13.1-ohio/kernel/drivers/dsld/kdsldmod.ko
	 599740 bin/busybox
	 551944 usr/bin/telefon
	 473772 lib/modules/2.6.13.1-ohio/kernel/drivers/net/wireless/avm_wlan/wlan/tiap.ko
	 436344 usr/sbin/nmbd
	 413184 lib/libuClibc-0.9.28.so
	 372060 usr/bin/screen.bin
	 323371 lib/modules/2.6.13.1-ohio/kernel/fs/cifs/cifs.ko
	 314836 lib/libavmcsock.so.2.0.0
	 303784 lib/modules/microvoip-dsl.bin
	 283853 lib/modules/microvoip_isdn_top.bit1
	 274704 usr/bin/ctlmgr
	 274352 lib/libsiplib.so.2.0.0
	 273900 usr/lib/libncurses.so.5.5
	 259052 lib/libssl.so.0.9.8
	 252344 usr/share/ctlmgr/libtr069.so
	 234684 usr/share/ctlmgr/libfon.so
	 212468 lib/modules/microvoip_isdn_top.bit
	 212432 sbin/dsld
	 204336 usr/bin/lua
	 202684 lib/libmscodex.so.2.0.0
	 200256 usr/lib/libreadline.so.5.2
	 183224 usr/sbin/dropbearmulti
	 167180 sbin/fsck.ext2
	 163360 sbin/multid
	 155037 lib/modules/2.6.13.1-ohio/kernel/drivers/usb/core/usbcore.ko
	 154224 usr/bin/wpa_authenticator
	 142624 lib/modules/2.6.13.1-ohio/kernel/drivers/atm/avm_atm/tiatm.ko
	 142104 lib/libosipparser2.so.4.0.0
	 132296 lib/libar7cfg.so.1.0.0
	 132124 lib/modules/2.6.13.1-ohio/kernel/drivers/scsi/scsi_mod.ko
	 131614 usr/share/samba/unicode_map.850
	 117746 usr/lib/mc/mc.hlp
	 116804 bin/voipd
	 116148 lib/libm-0.9.28.so
	 106192 lib/modules/fw_dcrhp_1150_ap.bin
	 102712 usr/lib/libext2fs.so.2.4
	 102472 sbin/fdisk
```

We can see that Samba, MC, and Screen seem quite large, but the whole
thing is not really clear yet because the files from the original
firmware analyzed earlier are still in the list. If we want to see only
those that occur exclusively in the mod, we first have to filter a
little:

```
	$ cd build
	$ find original/filesystem -type f | sed 's/^original\/filesystem\///' > orig-files
	$ find modified/filesystem -type f | sed 's/^modified\/filesystem\///' > modi-files
	$ diff -u orig-files modi-files | \
		grep '^+' | grep -v '^+++' | sed 's/^+/modified\/filesystem\//' > new-files
	$ cat new-files | xargs ls -lSR | more

	 913456 usr/sbin/smbd
	 779956 usr/bin/mc.bin
	 436344 usr/sbin/nmbd
	 372060 usr/bin/screen.bin
	 323371 lib/modules/2.6.13.1-ohio/kernel/fs/cifs/cifs.ko
	 273900 usr/lib/libncurses.so.5.5
	 204336 usr/bin/lua
	 200256 usr/lib/libreadline.so.5.2
	 183224 usr/sbin/dropbearmulti
	 131614 usr/share/samba/unicode_map.850
	 117746 usr/lib/mc/mc.hlp
	  85680 lib/modules/2.6.13.1-ohio/kernel/fs/mini_fo/mini_fo.ko
	  85072 usr/lib/libmatrixssl.so
	  68816 usr/sbin/bftpd
	  57005 lib/modules/2.6.13.1-ohio/kernel/net/ipv4/netfilter/ip_conntrack.ko
	  34309 usr/lib/mc/syntax/html.syntax
	  31232 lib/modules/2.6.13.1-ohio/kernel/net/ipv4/netfilter/ip_tables.ko
	  26432 usr/lib/libhistory.so.5.2
	  24544 usr/bin/haserl
	  23940 usr/sbin/matrixtunnel
	  21708 usr/sbin/mount.cifs
	  20392 lib/modules/2.6.13.1-ohio/kernel/drivers/block/loop.ko
	  11461 usr/lib/mc/syntax/perl.syntax
	  10684 lib/modules/2.6.13.1-ohio/kernel/net/ipv4/netfilter/ipt_LOG.ko
```

We see several things: *Samba* is indeed a space hog when *smbd* and
*nmbd* are counted together. *MC* with *ncurses* is also not to be
ignored; perhaps we could at least leave out the help file *mc.hlp*.
However, with text-heavy files such as the MC help, expectations should
not be too high: **all our comparisons are basically flawed, because we
would have to look at the files LZMA-compressed to get an impression of
how much space they would actually need in SquashFS on the box. Text
files, for example, are extremely compressible. Leaving them out often
saves less than hoped.**

What also stands out are various *Netfilter* libraries that were probably
copied into the firmware when I once compiled *Iptables* as a test.
Obviously, quite a few things remain that do not belong in the firmware
anymore because they have long since been deselected. This also applies
to some shared libraries and various kernel modules. So please pay
attention and check; perhaps empty the corresponding directories, or if
you do not know where to touch, start over with a correctly set
configuration file (`.config`).

### Step 3: Before-and-After Comparison of Existing Files

So far we have looked at old and new files, but have not checked whether
files with the same names that exist in both firmware versions have
possibly changed significantly in size. This can also give hints about
where space can still be saved, although probably to a lesser extent. But
every little bit counts.

The following shell script may be a little confusing and is certainly not
programmed optimally, but it serves its purpose. I cannot use *awk*, by
the way, otherwise the whole thing would probably have become clearer.
What it does is this:

-   generate two file lists, as already seen above
-   filter out file names that appear in both lists, that is, keep them
-   generate another shell script and make it executable
-   execute the shell script
-   the script itself outputs, for all common files, the size difference
    (new minus old) in bytes and the path name
-   the result list is sorted ascending and filtered; files without a
    size difference are eliminated
-   we are then interested in the files with the largest absolute
    differences. Negative values mean space saved compared with the
    original firmware; positive values mean additional space used.

```
	$ cd build
	$ find original/filesystem -type f | sed 's/^original\/filesystem\///' > orig-files
	$ find modified/filesystem -type f | sed 's/^modified\/filesystem\///' > modi-files
	$ diff -u 99999 orig-files modi-files | grep '^ ' | sed 's/^ //' > before-after-files
	$ echo '#!/bin/bash' > before-after-script
	$ chmod +x before-after-script
	$ cat before-after-files | sed -r \
		's/(.*)/printf "%10d %s\\n" $(( $(stat -c "%s" modified\/filesystem\/\1) - $(stat -c "%s" original\/filesystem\/\1) )) \1/' \
		>> before-after-script
	$ ./before-after-script | grep -v ' 0 ' | sort -g > before-after-diffs

	-12468 lib/libuClibc-0.9.28.so
	 -7508 lib/libgcc_s.so.1
	 -3295 lib/modules/2.6.13.1-ohio/kernel/drivers/usb/core/usbcore.ko
	 -2184 lib/modules/2.6.13.1-ohio/kernel/drivers/scsi/scsi_mod.ko
	 -1088 lib/modules/2.6.13.1-ohio/kernel/fs/fat/fat.ko
	   ... ...
	  9756 lib/libpthread-0.9.28.so
	 10240 var.tar
    183108 bin/busybox
```

In this case we see nothing exciting: *uClibc* became about 12 KB
smaller, while *Busybox* became about 180 KB larger. That is not
negligible. However, Busybox can also do more than the original.

Was that useless? No. If we do the same with the 7050 firmware, we see
that *libgcc_s*, if selected in the configuration and therefore replaced,
shrinks from 215 KB to just under 60 KB; see
[there](http://www.ip-phone-forum.de/showpost.php?p=840715&postcount=17).
This is because in that firmware version the original was apparently
released by mistake without being stripped, or even with additional debug
information. Therefore, anyone modifying firmware and wanting to save
space should also pay attention to seemingly small details.

### More Space-Saving Tricks

### Moving Files Out

One option with great potential is moving files out, either to directly
accessible USB storage devices such as sticks or hard drives, or to
network drives mounted while the box boots using NFS, Cifsmount, or
Smbmount, so that files needed only after mounting can be loaded directly
from external storage or over the network. This allows firmware to be
built in `build/modified` that is actually too large for an image and
would abort during building, but which is then changed so large files are
replaced by symlinks to the storage to be mounted. The removed files are
provided accordingly, and the thinned-out `build/modified` is
successfully built into an image on the second pass. The startup scripts
of the firmware were also adjusted beforehand accordingly.

*Update 2007-10-05:* Since ds26-15.1, the package
[Downloader-CGI](http://www.ip-phone-forum.de/showthread.php?t=134934)
has been part of DS-Mod. It makes automatic downloading of files at box
startup easier.

### Compressed Binaries and Payload Data

An often voiced idea in IPPF is that one could use an EXE packer, for
example, to shrink binaries. This is **rather pointless** and only costs
unnecessary CPU time, because SquashFS, the filesystem of the boxes, is
already compressed so extremely well that further compression would not
really take effect; see
[there](http://www.ip-phone-forum.de/showthread.php?p=832868&highlight=lzma#post832868).
Why this sometimes leads to an apparently large amount of omitted data
barely saving firmware size, if the data is highly compressible, is
explained [in this
post](http://www.ip-phone-forum.de/showthread.php?p=844325&highlight=lzma#post844325).

### Older or Alternative Software Versions

People often ask in [IPPF](http://www.ip-phone-forum.de/) why, for
example, *Midnight Commander (mc-4.5.0)* or *Samba 2.0.10* are such old
versions. This is partly simply because the old versions are sufficient
in functionality, but much smaller than newer versions with more
features. In the case of *MC*, newer versions are also linked against
libraries that go a little beyond what *uClibC* offers as a *libc*
replacement, and replacing corresponding calls with custom macros would
mean a lot of effort.

Further saving opportunities consist of looking for alternatives to known
software packages. Examples:

-   *Matrixssl* is smaller than *OpenSSL* but is often sufficient, for
    example to build an HTTPS tunnel. Only if software based on SSL
    libraries, such as *OpenVPN*, does not work with *Matrixssl* and you
    believe you need it, is there no choice.
-   *Deco* is smaller than *MC*, but also significantly less powerful.
-   The *Rudi Shell* is fantastically small but can do a lot. It executes
    arbitrary shell scripts, has a command history, can transfer files to
    and from the box, even compressed, and is even suitable for remotely
    flashing the box. Together with *Matrixtunnel*, it becomes a
    functionally, though not comfortably, full replacement for *SSH* with
    far lower space requirements and without the need for SSH access,
    which behind some firewalls is simply not allowed because there is
    only a web proxy for HTTP and HTTPS. Rudi + Matrixtunnel is enough
    for that. Rudi cannot make *vi* remotely controllable, but files can
    simply be transferred back and forth instead. Edit locally in comfort,
    send back to the box, done.
-   *Cifsmount* connects to Windows and Samba shares but is significantly
    smaller than *Smbmount*.
-   *Mini_fo* is smaller than *UnionFS* but runs very stably; so far I do
    not know of any error reports about it in the forum. A *Mini_fo*
    mount cannot be exported via NFS, but who needs that? Besides, there
    is Samba, and that works.
-   *Perl* or *PHP* would overload the FritzBox in terms of resources;
    *Lua* would not. *Lua* is a very lean, easy-to-learn, and powerful
    scripting language, not only for CGI. *Update 2007-10-05:* I have
    since learned that Apache + PHP, which can now also be built with
    Freetz, can indeed run stably and performantly on the FritzBox, but
    the space consumption is enormous. And saving space is what this is
    about.
-   Speaking of CGI handling: *Haserl* is small and provides everything I
    need on the box. I do not even need *Lua* for that, and sometimes I
    even skip Haserl because a shell script is enough.

### Firmware Patches from Menuconfig

For a long time there have been firmware patches that remove unneeded
original components from the firmware image and create room for
additional packages. Everyone has to decide for themselves whether they
need help texts and assistants for the AVM web interface, the original
AVM web server itself (replaceable by BusyBox httpd), UPnP, DSL, VoIP,
parental controls, and so on.

For example, anyone running their box purely as an IP client that gets
internet access through an upstream router and does not need PPPoE login
can save a lot of space with a corresponding patch that removes *dsld*
and accessories from the firmware. Normal users use the box as a DSL
router and then cannot apply that patch.

Example web server: according to current knowledge, the AVM web server
can be dispensed with without problems and replaced by the smaller,
more resource-friendly *httpd*, which is used by Freetz anyway.
Unfortunately, in newer firmwares with the new AVM web interfaces since
around mid to late 2007, the AVM server was implemented differently, so
the *httpd* replacement is no longer possible.

Example UPnP: anyone who does not query the box status with client
programs, for example from AVM, via Universal Plug'n'Play (UPnP) - the
web interface is completely sufficient for me personally - or does not
want to allow client programs to dynamically change firmware settings,
that is, drill holes into them, can also omit the corresponding
components (`igdd` and other files). This saves space in the firmware
image, and one less process runs. Omitting UPnP makes sending faxes with
FritzFax impossible, however. Anyone who can do without that can deselect
UPnP.

### Closing Words

That should be enough for now. As said at the beginning, there are surely
many other saving opportunities. I will gladly add suggestions to this
page. With that in mind:

**Cheapskating is not cool, it is stupid; but *sensible* saving is
helpful.**

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)