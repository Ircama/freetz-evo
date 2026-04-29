# Flash Partitioning

The flash of every FRITZ!Box model contains the following functional
units:

-   Bootloader: ADAM2 / EVA (+ factory settings)
-   Kernel: Linux 2.4.17_mvl21-malta-mips_fp_le, 2.6.13.1-ar7/ohio
    or higher *(gzip or lzma compressed)*
-   Filesystem:
    [SquashFS](http://de.wikipedia.org/wiki/Squashfs)
    *(gzip or lzma)* or
    [YAFFS2](http://de.wikipedia.org/wiki/YAFFS2)
-   Configuration files + environment: TFFS

Over the years, several "flavors" of flash layout evolved for
FRITZ!Boxes. The basic concept comes from TI and its ADAM2 bootloader,
which manages the partition tables. Regardless of the order in memory, it
was defined that `mtd0` should contain the root filesystem, `mtd1` the
kernel, `mtd2` ADAM2 itself, and `mtd3` the configuration. The latter has
to be written frequently, must nevertheless remain error-free, and wears
out the flash in the process. To make this safer, AVM developed TFFS,
which uses double buffering and therefore needs two equally sized
partitions, `mtd3` and `mtd4`.

ADAM2, and later AVM's functionally equivalent replacement EVA, is
installed at the factory and was updated only in rather rare special
cases. A firmware update, on the other hand, always updates the kernel and
root filesystem; in the original concept this was done with the included
files `filesystem.image` for `mtd0` and `kernel.image` for `mtd1`.

Over the years, it became clear that the space requirements for kernel
and filesystem are hardly predictable in the long term, and that
partitioning itself became an obstacle because both components grew at
different rates. Several clever variations were created to bypass this
barrier. Starting with kernel 2.6, the separation was then abandoned
entirely to avoid the problem. On newer models with, by comparison,
almost unlimited NAND flash, the separation was reintroduced.

**Warning:** all `mtd` numbers mentioned in this article refer to the
partition tables stored in the environment. The numbers of the `mtd`
devices reachable from Linux are assigned by the kernel and often differ
from the ADAM2/EVA numbering.

To access the environment from Linux, there is the ADAM2 API, reachable in
different places under `/proc` depending on the kernel version.

To read the environment `mtd` table under kernel 2.4, use:

```
	cat /proc/sys/dev/adam2/environment | grep mtd
```

Starting with kernel 2.6, it must look like this:

```
	cat /proc/sys/urlader/environment | grep mtd
```

The list of all Linux `mtd` devices is obtained with:

```
	cat /proc/mtd
```

Because the Linux partitions are determined by the MTD drivers in the
kernel, numbering and sizes sometimes differ considerably from the
partitioning in the environment.

The following sections examine all partition schemes used.

### Hidden SquashFS

[![Flash Legende](../../screenshots/55_md.png)](../../screenshots/55.png)

The following firmware uses Hidden SquashFS in NOR flash with kernel 2.4:

-   2 MB Flash
    -   Fritzbox SL (03.48 bis 03.73)
    -   Fritzbox 2030 (03.73 bis 03.80)
-   4 MB Flash
    -   Eumex 300 IP (alte)
    -   Fritzbox (03.29 bis 4.02, auch int)
    -   Fritzbox SL WLAN (03.65 bis 04.15)
    -   Fritzbox WLAN 3030 (03.65 bis 04.15)
    -   Fritzbox WLAN 3050 (03.63 bis 04.07)
    -   Fritzbox Fon (03.37 bis 04.27, auch int)
    -   Fritzbox Fon 5050 (03.69 bis 04.26)
    -   Fritzbox Fon ATA (03.64 bis 04.28-Beta, auch int)
    -   Fritzbox Fon WLAN (03.42 bis 04.27, auch int)
    -   Fritzbox Fon WLAN 7050 (03.58 bis 4.01)

The Hidden SquashFS starts directly after the kernel, with 256 bytes of
padding, and mainly contains drivers. It is mounted during boot in the
startup script `rc.S`. The kernel and Hidden SquashFS are in
`kernel.image`, while the root filesystem is in `filesystem.image`. This
technique was used to separate proprietary binary modules from TI from
the root filesystem. The Hidden SquashFS contains files such as
`avalanche_cpmac.o`, `avalanche_usb.o`, and `tiatm.o` without any
subdirectories and is mounted at
`/lib/modules/2.4.17_mvl21-malta-mips_fp_le/kernel/hidden`.

[![Flash Hidden Squashfs](../../screenshots/56_md.png)](../../screenshots/56.png)

### Contiguous SquashFS

[![Flash Legende](../../screenshots/55_md.png)](../../screenshots/55.png)

The following firmware uses Contiguous SquashFS in NOR flash with kernel
2.4:

-   2 MB Flash
    -   Fritzbox SL (03.92 bis 03.94)
    -   Fritzbox 2030 (03.92 bis 03.93)
-   4 MB Flash
    -   Fritzbox Fon WLAN 7050 (04.03-Beta bis 04.26, auch int)

With Contiguous SquashFS, the root filesystem starts directly after the
kernel, with 256 bytes of padding. Since the root filesystem is now spread
across `mtd0` and `mtd1`, the firmware update must split it accordingly
between `kernel.image`, kernel plus beginning of the root filesystem, and
`filesystem.image`, the rest of the root filesystem. This technique was
used to borrow space for the growing root filesystem from the kernel
partition without repartitioning.

[![Flash Contiguous](../../screenshots/57_md.png)](../../screenshots/57.png)

### Hidden Root

[![Flash Legende](../../screenshots/55_md.png)](../../screenshots/55.png)

The following firmware uses Hidden Root in NOR or serial flash with kernel
2.6:

-   all firmware from kernel 2.6.13.1 onward that does not use NAND Root

With Hidden Root, the root filesystem, similar to Contiguous SquashFS, is
located directly behind the kernel, with 256 bytes of padding. These boxes
can be recognized by the start and end address of `mtd0` both being 0 in
the `mtd` table and by `filesystem.image` being empty in the firmware
update. `kernel.image` contains both the kernel and the root filesystem.
This technique was used to dynamically divide the available space between
kernel and root filesystem without being constrained by partition borders.

[![Flash Hidden Root](../../screenshots/58_md.png)](../../screenshots/58.png)

### NAND Root

[![Flash Legende](../../screenshots/55_md.png)](../../screenshots/55.png)

The following models use NAND Root with kernel 2.6:

-   Fritzbox 3272
-   Fritzbox 3370
-   Fritzbox 3390
-   Fritzbox 6840 LTE
-   Fritzbox 7272
-   Fritzbox 7362 SL
-   Fritzbox 7490

All partition schemes mentioned so far are based on parallel or serial NOR
flash with predictable storage space.
[NAND-Flash](https://de.wikipedia.org/wiki/NAND-Flash)
can already contain errors from the factory and can therefore be used
reliably only with error-detection mechanisms. This requires special
controllers or filesystems that manage lists of defective blocks. The
storage space is therefore no longer necessarily continuously usable and
can no longer be written without intelligence, unless one wants to destroy
the list of defective blocks, which would be very unwise.

On models that use NAND only as data storage for the NAS, for example the
7390, this is not a problem. This storage is addressed intelligently only
from Linux and normally contains no system components. All partitions that
are recovered through the bootloader are located in NOR flash.

Models where the system itself is also in NAND flash only have a small
serial NOR flash for the bootloader `mtd2` and two TFFS partitions, `mtd3`
and `mtd4`. All other partitions are in NAND flash. Since NAND does not
have a space problem, two partitions each were provided for kernel and
filesystem. This has the advantage that the running system can be updated,
that is, it is hot flashable. The two partitions not currently in use are
written, marked active, and the system is restarted. On the next update,
the process switches the active partitions again. The kernel is on `mtd1`,
the filesystem is again separate on `mtd0`. Which two partitions are meant
is defined by the EVA variable `linux_fs_start`.

[![Screenshot](../../screenshots/277_md.png)](../../screenshots/277.png)

To continue using the advantages of efficiently compressible SquashFS
independently of the filesystem used, AVM chose an interesting concept. A
minimal wrapper system is installed on the filesystem partition; it
consists of only 190 inodes and the actual system
`filesystem_core.squashfs`. The latter is mounted as `/` via a loop
device. This naturally requires more RAM, but has the additional advantage
of being faster and putting significantly less strain on the NAND flash.

The two very sparse TFFS partitions in NOR flash serve only factory setup,
EVA, and recovery. During operation, a new config partition in NAND flash
is used, using YAFFS2 to store the configuration.

These "NAND Root" models also required a completely redesigned mechanism
for updating and recovery.

WIP

### Filesystem

Basically, every FRITZ!OS-based firmware image contains at least one
[SquashFS](http://de.wikipedia.org/wiki/Squashfs)
filesystem. It is almost always compressed with lzma or gzip, and only
rarely uncompressed. Models with Hidden SquashFS contain two filesystems
side by side in the firmware; models with NAND Root contain two nested
filesystems.

A SquashFS image contains an always-uncompressed superblock that starts
with the signature `sqsh` for big endian or `hsqs` for little endian.
This distinction is very important because all further data uses the
respective endian format. The superblock can be read with any variant
using `unsquashfs -s`. Unfortunately, there are many SquashFS variants, no
global standard, and no tool that works for all variants. FRITZ!Box uses
three SquashFS generations, versions 1 to 3. This version number is stored
in the superblock as `versionmajor`. `versionminor` serves as a substitute
for the forgotten field specifying the compression type. 0 and 1 mean gzip
compression, which every standard `unsquashfs` supports. 76 is the most
common value on the FRITZ!Box and represents lzma compression. Because
this is not a standard, Freetz builds `tools/unsquashfs3-lzma`. To avoid
confusing it with a plain version number, the notation with `:` separating
major and minor has become established, for example `3:76`.

Analysis of 1800 different unmodified firmware, lab, and recovery images
showed this distribution:

-   1:0 - SquashFS 1, gzip compressed - approx. 0.1%
-   2:0 - SquashFS 2, gzip compressed - approx. 0.5%
-   2:1 - SquashFS 2, gzip compressed - approx. 8%
-   2:76 - SquashFS 2, lzma compressed - approx. 23%
-   3:0 - SquashFS 3, gzip compressed - approx. 12.2%
-   3:76 - SquashFS 3, lzma compressed - approx. 56.5%

The images listed as 3:0 are the `filesystem.image` and the contained
`filesystem_core.squashfs` of NAND Root models; both are gzip compressed.
There are also newer SquashFS 4 variants that support `xz` compression,
but they have not yet been used on the FRITZ!Box.

Recoveries also contain SquashFS in binary form, in the `.data` section,
which can easily be isolated with 7zip. There one can search for the two
signatures and mask out false matches with implausible major/minor values.
The size of the SquashFS is normally in the superblock as `bytesused`, but
the value can also be 0. This is not really a problem, because a SquashFS
is not disturbed by superfluous data at the end.

There is a share of recoveries, about 5%, unfortunately including three
newer ones, that do not allow extraction. Run-length encoded firmware
parts were found, pointing to over-optimizing compilers. In some older
recoveries with Contiguous SquashFS, the SquashFS signature is at the end
of the `.data` segment, so the truncated SquashFS is not automatically
findable before the kernel. In both cases, the extracted data material is
unusable.

Recoveries with Contiguous SquashFS, ten are known so far, can be
extracted if the position and length of the larger SquashFS part are
known. Run-length encoded recoveries can be extracted only with binary
patches generated by `bsdiff` from the extracted data material. The latter
are quite small, 1.5-3.5 KB, but can be created only if firmware or a
partition dump of the same version exists. Dumps of very old versions are
difficult to create because flashing them usually requires an older
bootloader.

### Kernel

The FRITZ!OS kernel is always compressed. Three techniques are used,
depending on the installed bootloader.

All kernels that can run on ADAM2 begin with the hex sequence
`42 FA ED FE` (0xFEEDFA42), the ADAM2 signature for MIPS-LE. Since ADAM2
did not yet have built-in support for compressed kernels, these contain a
`zimage` decompressor ([TI Avalanche
Inflater](http://gpl.back2roots.org/source/fritzbox/ALL_4.06/GPL-release_kernel/linux/arch/mips/mips-boards/ti_avalanche/inflater/),
8.5-12.5 KB) before the actual gzip-compressed kernel. It can also be
recognized by the string `zimage` within the first 13 KB of the kernel.
The beginning of the kernel data can be found by the gzip signature
`1F 8B 08`. ADAM2 kernels can also run on EVA.

All kernels that require EVA begin with the hex sequence `81 12 ED FE`,
independent of endian. A second signature starting at offset 12 (0x0C)
signals the type of compression used for the following kernel data. The
hex sequence `01 02 5A 07` means `lzma`; `10 20 5A 70` means `zlib`
compression, again independent of endian.

Analysis of 1800 different unmodified firmware, lab, and recovery images
showed this distribution:

-   zimage - gzip-compressed kernel 2.4 for ADAM2 or EVA - approx.
    10,2%
-   zlib - raw zlib stream with kernel 2.6 for EVA - approx. 0.1%
-   lzma - lzma stream with kernel 2.4 or 2.6 for EVA - approx. 89.5%

EVA was therefore already introduced under kernel 2.4. Of all examined
kernel 2.4 samples, about 75% were `zimage` compressed; the rest already
requires EVA because of lzma. All kernel 2.6 firmware requires EVA.

The two signatures can be used to find ADAM2 and EVA kernels in
recoveries. Checking the three compression signatures allows false matches
to be masked out. As with SquashFS, this works for run-length encoded
recoveries, eleven are known so far, only with binary patches generated
by `bsdiff` from the extracted data material. Interestingly, the patches
for the kernel are three times larger than the patches for the much larger
SquashFS. More research is clearly needed here.

### Weblinks

-   [Avalanche MTD Treiber, Kernel
    2.4](http://gpl.back2roots.org/source/fritzbox/ALL_4.06/GPL-release_kernel/linux/drivers/mtd/maps/avalanche-flash.c)


