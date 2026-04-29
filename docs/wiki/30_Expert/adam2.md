# ADAM2 Bootloader

ADAM2 is a bootloader from Texas Instruments that performs tasks similar
to a PC BIOS. ADAM2 was used by AVM in modified form in early FRITZ!Box
models with kernel 2.4, and even before kernel 2.6 was introduced it gave
way to AVM's own development EVA, which from a user perspective is almost
functionally identical. Because of the many parallels, both variants can
be regarded as "the bootloader" and only need to be distinguished in
individual cases.

The bootloader's tasks are:

-   initialize the hardware
-   detect the flash
-   detect and test the RAM
-   manage partitioning and basic factory settings
-   provide a serial console
-   provide a small FTP server (for recovery)
-   manage the environment in TFFS
-   boot the installed kernel

### Creating a Bootloader Backup

Anyone who wants to can create a bootloader backup, but should urgently
remember \*exactly which\* box it came from (MAC address). More about
that in the next section.

The size of the bootloader is stored in the environment variable `mtd2`,
which is set permanently in the bootloader itself.

From Linux, this partition often has a number other than `2`, which can
be found with the following command:

```
	cat /proc/mtd
```

One of the partitions listed there is called `bootloader` or `urlader`.
With its number, here for example `3`, the corresponding `mtdblock`
device can then be read:

```
	cat /dev/mtdblock3 > bootloader.bin
```

See also 'Backing Up Flash Partitions While Running'.

ADAM2 is always 64KB, EVA is 64KB on older models and 128KB or 256KB on
newer models. On the IAD 7570, the `mtd2` partition is 256KB, but the
upper 128KB are empty (0xFF). This could indicate a planned, but
technically impractical, second bootloader instance. The bootloader size
must absolutely be taken into account when developing aliens. An
unadjusted `install` script for 64KB bootloaders destroys a 128KB
bootloader without warning. This also applies to the AVM web interface;
the box will predictably become a brick.

Therefore, anyone developing aliens without checking the environment of
the target device and comparing it with the `install` script puts devices
at risk. Such risky experiments should therefore also be unlockable in
trunk only with effort (implemented: new non-GUI-activatable "Real
Developer" risk mode).

### Overwriting the Bootloader

Short answer: **NO!**

The bootloader contains many pieces of information that make a box
unique; on many WLAN models it also contains calibration data without
which the device is no longer the same.

Transferring it is therefore gross nonsense. Even if these details were
adjusted correctly, there is an even more fatal problem:

Even identical models were equipped with different flash and RAM chips
depending on availability, especially RAM chips with significantly
different characteristics such as number of banks, timing, and so on.
These differences are stored by undocumented configuration in the
bootloader. AVM bootloader updates transfer this information.

**A bootloader cannot be transferred safely even between identical
models.**

Without RAM, even an intact bootloader does not work ⇒ brick.

To restore the backup created above \*to exactly the same box\*, this
\*would\* be the way:

```
	cat bootloader.bin > /dev/mtdblock3
```

Even then there is a brick risk. The MTD drivers do not block the OS. If
another process accesses the environment during this, for example through
the ADAM2 API, the system may hang during the write or erase operation ⇒
brick.

In principle, the bootloader should therefore be written only with
suitable AVM firmware or when tools for debricking (EJTAG) are available.

### Bootloader Commands

-   Commands usable through the serial console can be found in the
    [ADAM2
    Shell](http://www.wehavemorefun.de/fritzbox/ADAM2_Shell)
    article.
-   Commands usable through FTP can be found in the
    [TinyFTP](http://www.wehavemorefun.de/fritzbox/TinyFTP)
    article.

On some models, the ADAM2 shell was removed for security reasons. This
does not affect devices sold through regular retail channels, only
provider models such as the FRITZ!Box Cable.

Through FTP, only models with at least one LAN port can be reached and
recovered. Models without LAN, such as some repeaters, are therefore not
suitable for experiments or for Freetz. Rough rule of thumb: if AVM
provides a recovery, the device is perfectly suitable for Freetz. This
does not automatically apply to devices provided by smaller providers.
They may contain so-called "Provider Additives" that survive a factory
reset. Newer recoveries refuse to operate on such devices; older
recoveries destroy the additive, irreparably without on-site help from
the provider. This is probably why AVM removed the [7570
Recovery](ftp://ftp.avm.de/fritz.box/fritzbox.fon_wlan_7570/x_misc/english/)
from the FTP server.

For AVM Speedports there were only factory-internal recoveries for
Telekom service. Unfortunately, these were never published.

**Warning: defective Speedport (sp2fr) recoveries that brick every
Speedport are also circulating on the net.**

Speedports can also be recovered cleanly with Freetz with little effort.
Warning: how-tos, forum posts, and Windows tools recommending MTD3/4
clean are either ancient or a botched laziness hack. Details about the
partly fatal consequences of this fossil bad habit follow.

### Bootloader Source Code

ADAM2 was supplied to many buyers of TI chips and was never actually open
source. Each device manufacturer then modified it according to its own
needs and kept the source code closed, including AVM. Linksys also used a
modified ADAM2 version, but accidentally leaked the source code in a
wag54g tarball. That did not change ADAM2's proprietary status, but at
least the Linksys variant became "Visible Source" and can be browsed
[here](http://gpl.back2roots.org/source/WAG54GV2/src/Adam2/). This
variant is, however, only of very limited significance for the FRITZ!Box.

The source code of AVM's ADAM2 variant was never published. Only the
[ADAM2
API](http://gpl.back2roots.org/source/fritzbox/ALL_4.06/GPL-release_kernel/linux/drivers/adam2/)
for reaching the environment was open source.

The successor EVA is not based on ADAM2 and is a complete,
function-compatible rewrite. Unlike ADAM2, EVA directly supports
compressed kernels and has so far been ported to at least 8
architectures. ADAM2 was used only on AR7 models with kernel 2.4. All
firmware generated by Freetz requires kernel 2.6 and EVA.

### Bootloader Structure

At the beginning of every MIPS bootloader there is an 8-byte
"signature". In reality, it is assembler code for initializing the MIPS
core, which MIPS kindly asks not to change. This instruction sequence
clears two halves of a debug register (watchpoint exception when
"touching" an address) that are not used in normal operation, and because
of its length it is also excellently suited as a reliable signature. See
the comment "First thing: clear watch regs" in this
[source](http://gpl.back2roots.org/source/WAG54GV2/src/Adam2/src/avreset.S).

For Little Endian models (AR7, UR8), this assembles to the hex sequence
`00 90 80 40 00 98 80 40`, which is always found at the beginning of
`mtd2`, meaning the entire flash. On Big Endian models (AR9, AR10, VR9,
Fusiv), it corresponds to the 32-bit mirrored hex sequence
`40 80 90 00 40 80 98 00`, and additional data is always located before
it. This is a
[vector table](https://dev.openwrt.org/browser/trunk/package/uboot-ifxmips/files/cpu/mips/danube/start.S)
of up to 1024 bytes, or cold and warm start vectors and code for
initializing the EBU unit mentioned
[here from line
44](http://code.metager.de/source/xref/denx/u-boot/arch/mips/cpu/mips32/start.S#44).
On AR9, AR10, and VR9 this is 24 bytes (offset 0x18), on Fusiv the full
1024 bytes (offset 0x400). These bytes naturally belong to the
bootloader; the two "signature instructions" merely shift as a result.

These signatures are not suitable for masking out ARM bootloaders,
because ARM assembler has different frequency distributions. A reliable
detector must therefore first recognize ARM code. There is also a
reliable assembler sequence from low-level initialization for detecting
Puma5 (ARM1176BE) bootloaders. See the comment "Unlock CFG MMR region"
in
[this](http://gpl.back2roots.org/source/puma5/netgear/CMD31T_GPL/ti/psp_uboot/src/u-boot-1.2.0/cpu/arm1176/puma5/puma5.h)
and
[this](http://gpl.back2roots.org/source/puma5/netgear/CMD31T_GPL/ti/psp_uboot/src/u-boot-1.2.0/board/tnetc550/lowlevel_init.S)
source. It assembles to code containing the hex sequence
`08 61 1A 38 83 E7 0B 13 08 61 1A 3C`. Unfortunately, this signature is
not found at the beginning of the bootloader. On the 6360 with EVA 2070
it is at offset 0xF1AC, still within the first 64KB of Puma5 EVA.
Unfortunately, no recoveries are available to test the signature. It
works perfectly with Puma5 EVA or [U-Boot
code](http://gpl.back2roots.org/source/puma5/netgear/CMD31T_GPL/ti/psp_uboot/src/u-boot-1.2.0/board/tnetc550/lowlevel_init.o).

Regardless of offset, EVA can be recognized by the 32-bit value
`0x00000002` or `0x00000003`, in the respective endian, at offset 0x580.
This is the version (almost always 2, also 3 on very recent models) of
the EVA
[Urlader configuration](http://www.wehavemorefun.de/fritzbox/ADAM2#Urlader-Konfig),
where parts of the basic settings are entered at the factory. Since EVA
images in firmware contain no configuration, the value there is
`0xFFFFFFFF`. ADAM2 also contained parts of these settings, but compiled
in without a fixed offset.

Both bootloaders have 8 default MAC addresses compiled in,
`00:04:0E:FF:FF:01` - `00:04:0E:FF:FF:08`, the minimum requirement for
communication if the Urlader configuration is defective or not yet
present. Since development of the [VoIP Gateway
5188](http://www.wehavemorefun.de/fritzbox/5188), EVA also contains the
environment of the second CPU compiled in, because that CPU has no flash
of its own and therefore no TFFS or environment and boots through
NFSRoot. Environment variables can internally be addressed not only by
name but also by numeric index. For this purpose, a list of numerically
addressable variables was compiled in and always starts with `AutoMDIX`.
In older ADAM2 bootloaders the list ends after the last variable, for
example `wlan_key`; in newer ADAM2 and EVA it ends with `zuende`. This
table is open source because it is also the TFFS name table; see
"\#if defined(URLADER)" and "_TFFS_Name_Table" in
[tffs.h](http://gpl.back2roots.org/source/fritzbox/7270_5.05/GPL-release_kernel/linux/include/linux/tffs.h).

All recoveries contain fragments of at least one bootloader. In the early
days of the FRITZ!Box, identical firmware was renamed for several models,
but the bootloaders of those models had not yet been harmonized.
Accordingly, multiple bootloader signatures are found in recoveries from
that period, because the model-specific part was included multiple times,
but the cross-model part was not.

In principle, extracting a working bootloader from a recovery is not
possible, because the bootloader is intelligently assembled from code
fragments contained in the recovery and factory settings located on the
box. For model research, however, the ability to locate the fragments and
their basic settings is interesting. Of 436 analyzed recoveries, about
14% were ADAM2-MIPSLE, 50% EVA-MIPSLE, and the remaining 36% EVA-MIPSBE.
For all samples, analyzing the last 256 KB of the `.data` segment of each
recovery.exe, isolatable with 7zip, was sufficient.

During the switch to kernel 2.6, some models had to be switched to EVA.
Therefore some firmware updates contain a `urlader.image` and matching
programs for updating. In the beginning there were also a few ADAM2
updates whose filename contained model and version information, such as
`urlader.Fritz_Box_4MB.97.adam2.image`. Unlike the fragments in
recoveries, these are always fixed-size bootloaders with empty areas for
configuration to be transferred.

In ADAM2, the bootloader version is compiled in as an integer in the form
`urlader-version \x00 99 \x00`; before that variable existed, it appeared
as `$ProjectRevision: 1.24 $`, also with multi-digit versions as in
[this](http://www.akk.org/~enrik/fbox/OLD/boot-06.01.116.txt) boot log.
In EVA, the version is found up to 3 bytes before or after the character
sequence `%d.%s`, and 1000 must be added. An additional `M` indicates a
modified variant. Newer recoveries also contain a `.eva` filename, for
example the string `1717M.eva` for the 7360v2 with EVA 2717M. In 436
analyzed recoveries, ADAM2 versions 1.20, 1.24, 50 to 99 and EVA
versions 1124 to 2970 were discovered (as of 2014-01). For 5 EVA 1190
recoveries 04.30/31, version detection does not work; the number is
somewhere from offset 0xF000 relative to the signature. These must be
recognized by MD5.

The oldest bootloader found in firmware, ADAM2 version 1.24, was
discovered in the oldest known firmware so far,
fritz.box_sl.05.01.63.image from 30 April 2004, one month after the
first FRITZ!Box was presented at CeBIT. Four English bootloaders of
version 1.20 are newer. Because development was separate per model,
ADAM2 versions cannot be sorted chronologically. The oldest EVA
bootloader version found in firmware, version 1124, is in an early 7170
recovery. EVA versions can only be sorted chronologically across models
from around 1600 onward.

Recoveries contain two additional easy-to-find version details for the
program part. They say nothing about the contained firmware components.
Two examples each:

-   FW 3.37:
    `AVM Berlin recover-tool-version:[RECOVER:53][IO_CSP:11] compiled at Feb 18 2005 on 14:24:36`
-   FW 6.01:
    `AVM Berlin recover-tool-version:[RECOVER:378M][IO_CSP:248] compiled at Aug 23 2013 on 13:52:14`
-   FW 3.37:
    `[AVM Berlin Wizard Base Project, $ProjectRevision: 1.7 $, $Date: 2005/02/11 10:47:18Z $, kompiliert am Feb 14 2005 um 10:10:13]`
-   FW 6.01:
    `[AVM Berlin Wizard Base Project, $ProjectRevision: 1.63 $, $Date: 2011/07/04 11:49:20Z $, kompiliert am Jul  8 2013 um 11:45:45]`

As can be seen, the GUI (Wizard), recovery, and I/O components are
developed and compiled separately. A modern recovery therefore consists
of at least 6 projects. On older FRITZ!Box CDs, for example 3020, there
is a recover.exe without integrated firmware (about 100KB) that still
required an external image. The program is called `ar7recover` and dates
from February 2004, one month before the first FRITZ!Box was presented.
This is probably AVM's oldest published recovery solution.

Every recovery identifies a box using the Urlader variable `HWRevision`.
Since the Urlader has no access to the full model name, each recovery
contains a list of all HWRevisions known up to its creation date and
their model names. The list is located in the `.rdata` segment isolatable
with `7zip`; in older recoveries up to about 04.43, it is in the `.data`
segment or absent (so far only in one 03.14). The purpose of the list is
the human-readable display of the detected model in the GUI, regardless
of whether the recovery matches.

The list is up to 3 KB and always starts with the string `unknown`,
followed by null-terminated HWR / box-name pairs, with 32-bit padding per
string. The last entry is always `FRITZ!Box SL` and its HWR `F`. Some
lists assign HWR `K` to `unknown`; in others, the first model name
follows directly. Unfortunately, the assignment pairs are not consistent.
The list contains, for example, two consecutive names or numbers, but
also company names such as AVM and Telekom. It therefore has to be
interpreted intelligently. Although the HWR list is also included in
current recoveries, AVM has not maintained it since HWR 190. Recoveries
with higher values additionally contain the assignment entry for the
supported model in the `.data` segment: the HWR followed by several null
bytes followed by the name. Since in all newer recoveries the `.data`
segment starts with the null-terminated HWR, this can be used as a search
string in the last 256 KB of the segment. Whether and how foreign models
with HWR \> 190 are recognized in these recoveries still has to be
checked.

When analyzing 419 recoveries with the above knowledge, the frequency
distribution was determined. To mask out consistency errors, the list
contains only assignments found in at least 5 recoveries. The counters
for HWR \> 190 were previously multiplied by 10.

```
	Count	HWR	Box-Name
	416	G	FRITZ!Box
	417	F	FRITZ!Box SL
	416	58	FRITZ!Box Fon
	414	60	FRITZ!Box WLAN
	416	61	FRITZ!Box Fon WLAN
	417	62	FRITZ!Box (Annex A)
	416	63	FRITZ!Box SL (Annex A)
	416	64	FRITZ!Box Fon (Annex A)
	414	65	FRITZ!Box WLAN (Annex A)
	412	66	FRITZ!Box Fon WLAN (Annex A)
	69	71	FRITZ!Box Fon ata
	348	71	FRITZ!Box Fon ata / FRITZ!Box Fon ata 1020
	415	72	FRITZ!Box Fon 5050
	410	73	FRITZ!Box Fon 5050 (Annex A)
	408	76	FRITZ!Box Fon WLAN 7050
	410	77	FRITZ!Box Fon WLAN 7050 (Annex A)
	417	78	Eumex 300 IP
	415	79	FRITZ!Box WLAN 3070
	415	82	FRITZ!Box WLAN 3050
	415	83	FRITZ!Box 2030
	415	84	FRITZ!Box 2070
	415	85	FRITZ!Box WLAN 3030
	59	86	FRITZ!Box FON 5010
	341	86	FRITZ!Box Fon 5010
	341	87	FRITZ!Box Fon CTP
	59	87	FRITZ!Box FON CTP
	348	88	RadioFRITZ! 8000
	52	88	FRITZ!Box Radio
	338	89	FRITZ!Box Fon 5012
	59	89	FRITZ!Box FON 5012
	344	90	FRITZ!Box Fon WLAN 7170
	348	91	Sinus W 500V
	52	91	Sinus W 300V
	398	93	Speedport W 501V
	339	94	Unknown
	57	94	FRITZ!Box FON WLAN 7170
	59	95	FRITZ!Box FON WLAN 7140
	336	95	FRITZ!Box Fon WLAN 7140
	59	96	FRITZ!Box FON WLAN 7130
	337	96	FRITZ!Box Fon WLAN 7130
	52	97	Sinus W 500V
	348	97	Unknown
	348	101	Speedport W 701V
	348	102	Speedport W 900V
	317	103	VoIP Gateway 5144
	317	104	VoIP Gateway 5188
	31	104	FRITZ!Box Profi VoIP / FRITZ!Box Fon 5188
	343	105	FRITZ!Box Fon WLAN 7540V
	345	106	FT 7150 D
	341	107	FRITZ!Box Fon WLAN 7140 Annex A
	343	108	FRITZ!Box Fon WLAN 7141
	344	109	FRITZ!Box Fon WLAN 7170 SL
	5	110	FRITZ!Box Fon 5140 / FRITZ!Box Fon 5120
	343	110	FRITZ!Box Fon 5120
	342	111	FRITZ!Box Fon 5140
	309	112	FRITZ!Box WLAN 3130
	38	112	FRITZ!Box WLAN 3131
	348	113	FRITZ!Box 2031
	345	114	FRITZ!Box Fon 5122
	344	115	FRITZ!Box Fon WLAN 7122
	24	117	FRITZ!Box Fon WLAN 3170
	317	117	FRITZ!Box WLAN 3170
	303	118	FRITZ!Box WLAN 3131
	24	119	FRITZ!Box Fon 2170
	317	119	FRITZ!Box 2170
	295	120	FRITZ!Box W702V
	292	121	Speedport W 900 V
	291	122	FRITZ!Box Fon WLAN 7270
	295	123	FRITZ!Media 8020
	295	124	FRITZ!Media 8040
	295	125	FRITZ!Box 5124
	295	126	FRITZ!Box 5124 (Annex A)
	291	127	FRITZ!Box Fon WLAN 7170 (Annex A)
	295	128	FRITZ!Box 7150 / FRITZ!Box 7150 (Annex A)
	295	129	FRITZ!Box 7113
	295	130	FRITZ!Box 2121
	295	131	FRITZ!Box 5130
	295	133	FRITZ!Box 2110
	295	134	Speedport W721V
	281	135	Speedport W920V
	281	136	Speedport W503V
	258	137	FRITZ!Box WLAN 3270
	257	138	FRITZ!WLAN Repeater N/G
	257	139	Unknown
	257	140	FRITZ!Box Fon 5125 / FRITZ!Box Fon 5125 (Annex A)
	253	141	FRITZ!Box Fon WLAN 7270 (Annex A)
	257	142	Speedport W 721VK
	254	143	Speedport W 101 Bridge
	253	144	FRITZ!Box Fon WLAN 7240
	15	145	FRITZ!Box Fon WLAN 7270
	238	145	FRITZ!Box Fon WLAN 7270 v3
	253	146	FRITZ!Box Fon WLAN 7570 vDSL
	243	147	DSL-EasyBox A802
	14	147	DSL-EasyBox A802-R
	257	148	DSL-EasyBox A602
	257	149	DSL-EasyBox A402
	243	150	FRITZ!Box Ikanos
	243	151	FRITZ!Box 8160
	243	152	Speedport W722V
	240	153	Alice IAD 7570 vDSL
	238	154	FRITZ!Box Fon WLAN 7212
	240	155	FRITZ!Box Fon 5113 / FRITZ!Box Fon 5113 (Annex A)
	230	156	FRITZ!Box Fon WLAN 7390
	30	157	FRITZ!Box Fon WLAN 6360
	153	157	FRITZ!Box 6360 Cable
	230	159	FRITZ!Box Fon WLAN 7112
	234	160	Speedport W 504V
	234	162	FRITZ!Box 7113 (Annex A)
	183	164	FRITZ!Box Fon WLAN 504avm
	228	165	FRITZ!Box Fon WLAN 7541 vDSL
	183	167	FRITZ!Box Fon WLAN 7270 v4
	210	168	FRITZ!Box WLAN 3270 v3
	183	171	FRITZ!Box Fon WLAN 7340
	183	172	FRITZ!Box Fon WLAN 7320
	152	173	FRITZ!WLAN Repeater
	192	174	Alice IAD WLAN 3331
	186	175	FRITZ!Box WLAN 3370
	156	176	FRITZ!Box 6320 Cable
	153	177	FRITZ!Box 6840 LTE
	140	178	FRITZ!Box Fon WLAN 7313
	117	179	FRITZ!Box 7330
	25	179	FRITZ!Box Fon WLAN 7330
	143	180	FRITZ!Box 6810 LTE
	140	181	FRITZ!Box Fon WLAN 7360 SL
	60	182	FRITZ!Box 6322 Cable
	80	182	FRITZ!Box 6320 v2 Cable
	140	183	FRITZ!Box Fon WLAN 7360
	143	184	FRITZ!Box 6841 LTE
	30	185	FRITZ!Box 7490
	90	185	FRITZ!Box 7391
	117	186	FRITZ!Box 6361 Cable
	117	187	FRITZ!Box 6340 Cable
	117	188	FRITZ!Box 7330 SL
	117	189	FRITZ!Box 7312
	117	190	FRITZ!Powerline 546E
	40	192	FRITZ!Box 7272
	30	193	FRITZ!Box 3390
	10	195	FRITZ!Box 6842 LTE
	40	196	FRITZ!Box Fon WLAN 7360 v2
	28	197	Unknown
	10	197	FRITZ!Box WLAN 3270 v3
	20	198	FRITZ!Box 3272
	10	200	FRITZ!WLAN Repeater 450E
	30	203	FRITZ!Box 7362 SL
```

The HWR at the beginning of the `.data` segment is part of a structure
found in every recovery with kernel 2.6. In newer recoveries it is found
at offset 0, in older ones at offset 64 (0x40). The structure contains
the supported HWR at offset 0, the language at offset 16 (0x10), and the
space-separated list of supported brandings at offset 32 (0x20). This is
very useful because, for example, EWE recoveries are not recognizable by
filename. A fourth string whose exact purpose is still unclear normally
starts at offset 0x30 and shifts by 8 bytes each time the branding string
is longer than 8 bytes. In Congstar, and presumably also Telekom,
recoveries it contains `tcom`; in all others, independent of language and
provider, it always contains `avm`.

In all kernel 2.4 recoveries, a series of strings terminated by one or
more null bytes is located at the end of the `.data` segment. This is a
2- or 3-digit number of unknown purpose (unfortunately not the HWR) or
the string `IE`, the optional string `en` or `de`, and the firmware
version in dotted notation, for example `29.04.01`, with the optional
suffix `-prerelease-<checkpoint>`. After that comes the optional string
`avm` or `freenet`, followed by the optional list of supported brandings.
Only the oldest known recovery with integrated firmware (03.14) does not
contain this information. It is German and did not yet know branding. For
kernel 2.4 recoveries, the HWR must be determined from the Urlader.

Comparing the detected brandings with the `/etc` defaults confirms the
reliability of the above methods, both for release and lab recoveries.
However, there are 2 lab recoveries containing a wrong bootloader. The
file `FRITZ.Box_2110.04.47-9457.recover-image.exe` contains an HWR 130
bootloader of a 2121 that never reached the market; the file
`fritz.box_fon_wlan_7050.04.50.B.telnet.recover-image.exe` contains the
HWR 94 bootloader of a 7170.

### Bootloader and Freetz

Since Freetz requires EVA, some models are unsuitable for Freetz already
because of the bootloader. In principle, every box should be updated with
original firmware before applying Freetz. This may also update the
bootloader. For some older models, an
[intermediate update](ftp://service.avm.de/Zwischenupdate/) may be
necessary.

No EVA update exists for the following models:

-   FRITZ!Box (all versions)
-   FRITZ!Box SL
-   FRITZ!Box 2030
-   FRITZ!Box Fon (German A/CH Annex A+B) - possibly updatable to German
    or English with tricks
-   FRITZ!Box Fon ata (all versions)
-   FRITZ!Box Fon WLAN (German A/CH Annex A+B) - possibly updatable to
    German or English with tricks

For some of these models, Freetz could patch an EVA update from another
box as an alien. For the FRITZ!Box SL and 2030 with 2MB flash and 8MB
RAM, there will probably never be Freetz.