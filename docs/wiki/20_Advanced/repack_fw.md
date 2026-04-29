# Unpacking and Packing Firmware Images

If you want to unpack, change, and repack a firmware image, proceed as
follows. This is based on a guide by
[Alexander Kriegisch](http://www.ip-phone-forum.de/member.php?u=117253)
in [this forum thread](http://www.ip-phone-forum.de/showthread.php?t=175974).

### Tools and Syntax

The easiest approach is to use Freetz as infrastructure, specifically the
`fwmod` script from the Freetz main directory. When called without
parameters, it shows how it expects to be used:

```
	$ ./fwmod

	Usage: fwmod [-u|-m|-p|-a] [-i <cfg>] [-d <dir>] <orig_fw> [<tk_fw> [<aux_fw>]]
	  actions
		-u         unpack firmware image
		-m         modify previously unpacked image
		-p         pack firmware image
		-a         all: unpack, modify and pack firmware image (-u -m -p, default)
	  special actions
		-n         firmware-nocompile: do not install kernel and busybox
		-f         force pack even if image is too big for flash (AVM SDK)
		-z         zip file system into archive for USB/NFS root
		-c <dir>   copy file system to target directory for NFS/USB root (implies -z)
	  input/output
		-i <cfg>   input file for configuration data (default: .config)
		-d <dir>   build directory (default: <orig_firmware>.mod)
		<orig_fw>  original firmware name
		<tk_fw>    2nd firmware name (e.g. for merging in web UI)
		<aux_fw>   3rd firmware name (e.g. to borrow missing files)
```

You therefore need one call with `-u` to unpack, and after modifying the
firmware another call with `-p` to pack it again.

### Procedure

The following assumes that the user is in the main directory of a freshly
unpacked or checked-out Freetz tree, and that the firmware image to be
modified has already been downloaded into this directory. Then perform
these steps:

1.  First, create a suitable `.config` configuration file so that `fwmod`
	can find the required information when packing later. Run
	`make menuconfig` once, select the correct hardware, for example 7170,
	and leave the configuration, answering yes when asked whether to save.
2.  Before `fwmod` can be called for the first time, a few tools must be
	built. They will later be called indirectly to unpack and rebuild the
	firmware: `make tools`. This can take a while, several minutes.
	Internet downloads via `wget` must work.
3.  Now unpack the firmware image downloaded from AVM into a directory
	named `unpacked_firmware` in this example:

    ```
		./fwmod -u -d unpacked_firmware FRITZ.Box_Fon_WLAN_7170.29.04.59.image
    ```

4.  Then modify the firmware filesystem under
	`unpacked_firmware/original/filesystem`.
5.  Finally, pack the firmware image again:\

    ```
		./fwmod -p -d unpacked_firmware FRITZ.Box_Fon_WLAN_7170.29.04.59.image
    ```

This is the same call as before, only with `-p` instead of `-u`.
Unfortunately, the name of the original image must be specified even
though the image is not needed for packing. This is a small weakness of
the `fwmod` script.

6.  After a while, the end of the script output looks something like this:

    ```
		creating filesystem image
		merging kernel image
		 kernel image size: 6969088 (max: 7798784, free: 829696)
		packing 7170_.de_20080923-200251.image
		done.

		FINISHED
    ```

**Notes for Freetz versions up to and including 1.1:**

-   In these versions, both `fwmod` calls must be prefixed with this
	fakeroot part: `tools/build/bin/fakeroot -- `. `fwmod` expected to be
	called in a fakeroot environment and did not yet set that up itself.
-   If the error
	`` fakeroot: preload library `libfakeroot.so' not found, aborting. ``
	appears, prefixing the call with `LD_PATH_PRELOAD` helps:

    ```
		LD_PATH_PRELOAD=tools/build/lib/libfakeroot.so tools/build/bin/fakeroot -- ./fwmod ...
    ```

### Using fwmod in "no freetz" Mode

Since trunk changeset r13796, `fwmod` can be used in a quasi "no freetz"
mode. The flow is the same as building firmware modified by Freetz. In
this mode, however, no Freetz modification is made at all. Instead, a hook
is called in which custom firmware modifications can be implemented and
executed automatically. Proceed as follows:

1.  Run `make menuconfig`, enable expert mode, `Level of User Competence`
	= Expert, select the correct hardware, for example 7390, and then
	enable `Skip modifying unpacked firmware, adding Freetz stuff` under
	`Firmware packaging (fwmod) options`. This last step enables "no
	freetz" mode. Since Fritz!OS 6.5x, it is also recommended to enable
	`Sign image`, also found under `Firmware packaging (fwmod) options`;
	see the
	[Signing Firmware](http://trac_freetz_org/wiki/help/howtos/development/sign_image)
	article.
2.  Implement your own firmware modifications in the script
    [fwmod_custom](http://trac_freetz_org/browser/trunk/fwmod_custom)
	in the function
    [all_no_freetz](http://trac_freetz_org/browser/trunk/fwmod_custom?rev=13796#L14)
	. The unpacked root filesystem is available under `./filesystem`.
	`fwmod_custom` already contains some commented-out examples:
	[restore telnet
    support](http://trac_freetz_org/browser/trunk/fwmod_custom?rev=13796#L17),
    [restore debug.cfg
    support](http://trac_freetz_org/browser/trunk/fwmod_custom?rev=13796#L25).
3.  Then run `make`. The unpacked, `fwmod_custom`-modified, repacked, and
	possibly signed image can be found under `images/`.

    ```
		STEP 1: UNPACK
		unpacking firmware image
		removing NMI vector from SquashFS
		NMI vector v1 found at offset 0xBE0000, removing it ... done.
		splitting kernel image
		unpacking filesystem image
			Reading a different endian SQUASHFS filesystem on build/original/kernel/kernelsquashfs.raw
			Filesystem on build/original/kernel/kernelsquashfs.raw is lzma compressed (3:76)
			Parallel unsquashfs: Using 1 processor
			6112 inodes (6522 blocks) to write
			created 5328 files
			created 373 directories
			created 697 symlinks
			created 87 devices
			created 0 fifos
		unpacking AVM plugins
			tam image
			webcm_interpreter image
			wlan image
		unpacking var.tar
		done.

		detected firmware 7390_de 84.06.80 rev43122 (07.02.2017 12:23:41)

		STEP 3: PACK/SIGN
		WARNING: Modifications (STEP 2) and this step should never
				 ever be run with different configurations!
				 This can result in invalid images!!!
		WARNING: firmware does not seem to be modified by the script
		invoking custom script
		  restoring support for /var/flash/debug.cfg
			patching ./filesystem/etc/init.d/rc.tail.sh
		  checking for left over Subversion directories
		packing var.tar
		Image signing files found, checking their consistency
		Copying /home/gene/.freetz.image_signing.asc to /etc/avm_firmware_public_key9
		creating filesystem image
		  SquashFS block size: 64 kB (65536 bytes)
		merging kernel image
		  kernel image size: 14.6 MB, max 14.9 MB, free 0.3 MB (269568 bytes)
		  WARNING: Not enough free flash space for answering machine!
		adding checksum to kernel.image
		packing images/7390_06.80.de_20170220-222457.image
		  image file size: 16.8 MB
		signing images/7390_06.80.de_20170220-222457.image
		  signed image file size: 16.8 MB
		done.

		FINISHED
    ```


