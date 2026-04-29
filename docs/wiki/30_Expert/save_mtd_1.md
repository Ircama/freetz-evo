# Back Up Flash Partitions During Operation

This article builds on the article about flash partitioning. Reading it
first will not hurt.

The revised version of the article fills some gaps regarding the numbering
of devices. For that, our thanks go to
[Oliver
(olistudent)](http://www.ip-phone-forum.de/member.php?u=58639).

How to back up partitions directly through the Urlader/bootloader is
described further below.

### Motivation

I have never worked with the ADAM2 bootloader via FTP and will probably
do so only when necessary, or at most beforehand for practice. But to be
prepared for an emergency, I wanted to be able not only to make backups of
kernel and filesystem, but also to create a backup copy of the bootloader
itself, ideally without using ADAM2 directly, simply during operation via
shell scripts. This article describes how that works.

### Requirements

I have a FRITZ!Box Fon WLAN 7170, so I may count myself among the
well-equipped AVM customers, because the 7170 is currently the model with
the largest flash memory and the most extensive connection options. I do
not write this as advertising, but to make clear that the following does
not necessarily apply one-to-one to all other boxes, and probably does
not. In particular, numeric values must be adapted to the conditions of
other boxes.

The box has the following characteristics:

```
    {
      echo Kernel: $(uname -a)
      echo Firmware: $CONFIG_VERSION_MAJOR.$CONFIG_VERSION $CONFIG_SUBVERSION
      echo Flash-Partitionierung:
      cat /proc/sys/urlader/environment | grep mtd
    }

    # Kernel: Linux fritz.box 2.6.13.1-ohio #1 Sat Jan 27 12:00:36 CET 2007 mips unknown
    # Firmware: 29.04.29 ds-0.2.9     -->  _26-13
	# Flash partitioning:
    # mtd0    0x90000000,0x90000000   -->  Hidden Root, 0 KB
    # mtd1    0x90010000,0x90780000   -->  Kernel + Filesystem, 7.616 KB
	# mtd2    0x90000000,0x90010000   -->  ADAM2 bootloader, 64 KB
	# mtd3    0x90780000,0x907C0000   -->  TFFS for config data, 256 KB
	# mtd4    0x907C0000,0x90800000   -->  TFFS copy (double buffering), 256 KB
```

The notes after the arrows were added manually.

### Solution

Looking at the pseudo-filesystem `/dev/`, we quickly see the following
devices that apparently relate to our task:

-   `/dev/mtd0/` bis `/dev/mtd10`
-   `/dev/mtdblock0` bis `/dev/mtdblock10`

What is the difference between these devices? It looks as if they all
exist twice under different names. In a sense that is true, and we can see
why here:

```
    ls -l /dev/mtd*

    # crw-r-----    1 root     root      90,   0 Jan  1  2000 /dev/mtd0
    # crw-r-----    1 root     root      90,   1 Jan  1  2000 /dev/mtd1
    # ...
    # brw-r-----    1 root     root      31,   0 Jan  1  2000 /dev/mtdblock0
    # brw-r-----    1 root     root      31,   1 Jan  1  2000 /dev/mtdblock1
    # ...
```

The first letters of the file mode reveal it: `mtd*` are character
devices, abbreviation `c`; `mtdblock*` are block devices, abbreviation
`b`. In other words, there are two different views of flash memory: on
the one hand as a continuous character stream, on the other as a device
with block-wise direct access, like a hard disk. More details are in
[Wikipedia](http://de.wikipedia.org/wiki/Ger%C3%A4tedatei).

For the purpose of the backup, it basically does not matter how it is
created, character by character or block-wise, as long as we end up with
one complete file per flash partition on the hard disk. I tried both
variants and encountered unexplained phenomena with both, but backups work
better with the block devices, as we will see.

For the following explanations, I assume there is a mount point
`/var/fritz` representing larger storage. In my case, this is a Windows
share mounted via *smbmount*, but USB sticks or hard disks are also
possible. If there is enough free RAM on the box, the copies can also be
stored temporarily somewhere below `/var` and then transferred away via
FTP or SCP.

### Copies of Block Devices (`mtdblock*`)

I expected to be able to back up the ADAM2 bootloader, which according to
the Urlader configuration above should be in partition `mtd2`, with the
following command:

```
    cat /dev/mtdblock2 > /var/fritz/adam2
```

But no such luck. What do I find on my hard disk? A file of size
7,798,784 bytes, exactly 7,616 KB and therefore exactly the size of the
combination of kernel and directly following filesystem that actually
resides under `mtd1`. The whole thing seems related to numbering, because
this picture emerges:

```
	  ------------ ----------- ---------- ----------------------------------------------------------
	  Block device Partition   Size       Description
	  mtdblock0    ----        ----       *Endlosschleife beim Auslesen*
	  mtdblock1    mtd0        6.966 KB   SquashFS filesystem without kernel (rear part of mtd1)
	  mtdblock2    mtd1        7.616 KB   Kernel + SquashFS filesystem
	  mtdblock3    mtd2        64 KB      ADAM2 bootloader ("Urlader")
	  mtdblock4    mtd3        256 KB     TFFS for config data
	  mtdblock5    mtd4        256 KB     TFFS copy (double buffering)
	  mtdblock6    (mtd5)      1.664 KB   (Prepared for) JFFS2
	  mtdblock7    (mtd6)      5.952 KB   (Prepared for) kernel without JFFS2
	  ------------ ----------- ---------- ----------------------------------------------------------
```

The other three `mtdblock` devices produce output of length zero.

In summary: to get a copy of **partition `mtd[n]`**, one apparently has
to use the **block device `mtdblock[n+1]`**.

Note from
[maceis](http://www.ip-phone-forum.de/member.php?u=95502)
(29.12.2011):

> *I cannot observe this shift on my new 7270_v3. `cat /dev/mtdblock1`
> gives me a file exactly as large as the kernel, down to the KB.
> `cat /dev/mtdblock2` is 128 KB. This matches the output of
> `cat /proc/mtd` and `cat /proc/partitions`. The space for the Urlader
> has therefore apparently become larger. Why?*

Answer from [Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)
(06.01.2012):

> *I also no longer see the shift on my two boxes at the moment. This is
> probably related to firmware or Urlader versions and cannot be stated
> generally for all devices. The article is already quite old, and back
> then it was like that. As for the size of the Urlader: times apparently
> change here too. While, for example, the 7170, 7270_v1, and all older
> models had a 64 KB Urlader, the [7270_v2/3 have 128
> KB](http://www.wehavemorefun.de/fritzbox/index.php/7270#Environment).
> I would not rule out 256 KB on very new boxes either; I would have to
> investigate, I only have older devices.*

### Copies of Character Devices (`mtd*`)

Now it gets really confusing, because each partition appears twice in a
row among the character devices, although not all the way to the end
because numbering stops at 10:

```
	  -------------- ----------- ---------- ----------------------------------------------------------
	  Character dev. Partition   Size       Description
	  mtd0/1         ----        ----       *Endlosschleife beim Auslesen*
	  mtd2/3         mtd0        6.966 KB   SquashFS filesystem without kernel (rear part of mtd1)
	  mtd4/5         mtd1        7.616 KB   Kernel + SquashFS filesystem
	  mtd6/7         mtd2        64 KB      ADAM2 bootloader ("Urlader")
	  mtd8/9         mtd3        256 KB     TFFS for config data
	  mtd10(/11)     mtd4        256 KB     TFFS copy (double buffering)
	  (mtd12/13)     (mtd5)      1.664 KB   (Prepared for) JFFS2
	  (mtd14/15)     (mtd6)      5.952 KB   (Prepared for) kernel without JFFS2
	  -------------- ----------- ---------- ----------------------------------------------------------
```

The character devices in parentheses in the first column would exist if
`/sbin/makedevs` created them during boot. To obtain devices up to
`mtd15`, the following would have to be changed in `/etc/device.table`:

```
	# Current setting at AVM and in Freetz
	/dev/mtd        c       640     0       0       90      0       0       1       11

	# Changed setting (see last column)
	/dev/mtd        c       640     0       0       90      0       0       1       16
```

> *Quote from [Oliver
> (olistudent)](http://www.ip-phone-forum.de/member.php?u=58639):
> "In the original firmware it also stops at 10. I simply adopted it that
> way."*

Understandable, I would say. Everyone can change it for themselves if they
believe they need the devices.

The reason for the duplication, by the way, is that devices with even
numbers offer read-write access, while those with odd numbers offer
read-only access.

Here the formula is: to get a copy of **partition `mtd(n)`**, use the
**character device `mtd(2n+2)`**, or alternatively `mtd(2n+3)`.

### A Possibly Dangerous Tip, Without Warranty

In the
[OpenWRT-Forum](http://forum.openwrt.org/viewtopic.php?pid=18281#p18281)
you can read that the bootloader can supposedly be overwritten this way
during operation. Note the conditional wording; I do not know anyone here
in the forum who has tested it:

```
	# Assumption 1: the new bootloader is already under /var/adam2_new
	# Assumption 2: /dev/mtdblock3 corresponds to bootloader partition mtd2

	# Not like this: cp /var/adam2_new /dev/mtdblock3/
    cat /var/adam2_new > /dev/mtdblock3

    reboot
```

**Update (`cat` instead of `cp`, see above):** As described under
"Overwrite ADAM2", this works, as has been confirmed several times and as
AVM also demonstrates in firmware updates.

Who wants to try it? If it goes wrong and the bootloader is deleted
instead of overwritten, or the new image is bad, you can start preparing
the parcel for AVM, unless you are the lucky owner of a
[JTAG-Kabels](http://feadispace.fe.funpic.de/FBF7050/)
(see also
[OpenWrt.org](http://wiki.openwrt.org/OpenWrtDocs/Customizing/Hardware/JTAG_Cable))
with suitable software. If you accidentally overwrite "only" another
partition, recovery should be enough.

### Ways to Quickly Get an Overview

What I had wanted to describe for a long time, because I did not know it
when the original version of this article was written but later learned
through independent hints from [Sedat
(dileks)](http://www.ip-phone-forum.de/member.php?u=95274)
and [Enrik
(enrik)](http://www.ip-phone-forum.de/member.php?u=58906)
is that it would have been much easier to create the tables above for
partitions and block devices if I had known the following commands. Anyone
should run them on their box type to get an overview, because the
partitions are not the same size everywhere and do not have the same
numbering everywhere. For example, under kernel 2.4 the Urlader is found
under `/dev/mtdblock/2`, while under kernel 2.6 it is under
`/dev/mtdblock3`, a different number and one directory level higher. This
is important to know if, for example, you plan to downgrade to an older
firmware version that is also based on an older kernel and bootloader.
Writing the latter to the wrong partition achieves nothing.

### /proc/partitions

```
        $ cat /proc/partitions
    
        major minor  #blocks  name
    
          31     0       8192 mtdblock0
          31     1       6966 mtdblock1
          31     2       7616 mtdblock2
          31     3         64 mtdblock3
          31     4        256 mtdblock4
          31     5        256 mtdblock5
          31     6       1600 mtdblock6
          31     7       6016 mtdblock7
           8     0      64000 sda
           8     1      63984 sda1
```

Here you can clearly see the sizes of the individual partitions together
with device major/minor numbers, for those who need them, and matching
block device names.

On a 7270 this looks somewhat different:

```
	$ cat /proc/partitions

	major minor  #blocks  name

	  31     0       6732 mtdblock0
	  31     1        883 mtdblock1
	  31     2         64 mtdblock2
	  31     3        256 mtdblock3
	  31     4        256 mtdblock4
	  31     5       8192 mtdblock5
```

Here, `mtdblock2` really seems to be the bootloader.

### /proc/mtd

```
	$ cat /proc/mtd

	dev:    size   erasesize  name
	mtd0: 00800000 00010000 "phys_mapped_flash"
	mtd1: 006cdb00 00010000 "filesystem"
	mtd2: 00770000 00010000 "kernel"
	mtd3: 00010000 00010000 "bootloader"
	mtd4: 00040000 00010000 "tffs (1)"
	mtd5: 00040000 00010000 "tffs (2)"
	mtd6: 00190000 00010000 "jffs2"
	mtd7: 005e0000 00010000 "Kernel without jffs2"
```

In this alternative view, with partition sizes shown in hexadecimal
notation, the comment also contains a description indicating what each
partition is actually intended for. Very simple, very practical.

And here again the 7270:

```
	$ cat /proc/mtd

	dev:    size   erasesize  name
	mtd0: 00693200 00010000 "rootfs"
	mtd1: 000dce00 00010000 "kernel"
	mtd2: 00010000 00010000 "urlader"
	mtd3: 00040000 00010000 "tffs (1)"
	mtd4: 00040000 00010000 "tffs (2)"
	mtd5: 00800000 00010000 "reserved"
```

#### Backup of Urlader, Kernel, and Filesystem

How to back up `urlader.image` and `kernel.image` efficiently over the
network on kernel 2.6 firmware is described by me in the
[Forum](http://www.ip-phone-forum.de/showthread.php?p=954170#post954170).

### Notes on the 7270v3 with 2.6 Kernel (Tested with Version 74.04.88)

I can add the following information about the last "partition" to the
layout for the 7270 with the firmware mentioned above. The `mtd5` shown
as `reserved` in `/proc/mtd` contains the complete area from `mtd0` to
`mtd4` consecutively. The size of 16 MiB (0x800000) led me to this. If
the program `dd` with the functions `if` and `of` is integrated in
Freetz, both must be selected in menuconfig; tested with Freetz 1.2, a
complete backup can easily be created and restored:

```
	$ dd if=/dev/mtdblock5 of=/var/media/ftp/uStor00/mtd5.bak
```

Restoring works in reverse:

```
	$ dd of=/dev/mtdblock5 if=/var/media/ftp/uStor00/mtd5.bak
```

The program `cat` is equally suitable for backing up; its output must then
be redirected into the target file. The first inserted USB storage device
is usually mounted as `/var/media/ftp/uStor00`, though of course this can
be different in individual cases. With `bzip2`, it can be slightly
compressed if needed. For the copies, I have a script on the USB storage
device that regularly creates such a copy via cron.

I have tested this too: when the router was stuck in a reboot loop, I
successfully restored an earlier state by replaying such a copy.

Note that AVM can easily change the layout again in future versions, so
never simply type the command lines above without checking for yourself.
[Christoph
Franzen](http://www.ip-phone-forum.de/member.php?u=121255)

### Zusammenfassung

Anyone who wants copies of their flash partitions should do this during
operation by selecting the appropriate block device, be careful with
shifted numbering, and using `cat` to save the data to an external medium.
*ADAM2* is not strictly required for this; it works without it. It is best
to check the resulting file sizes to see whether the correct partitions
were captured. The bootloader is always 64 KB, TFFS is 256 KB, and the
rest depends on the box and firmware version.

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)


