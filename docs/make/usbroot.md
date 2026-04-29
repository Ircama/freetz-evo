# USB root 0.2 - DEPRECATED
  - Package: [master/make/pkgs/usbroot/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/usbroot/)
  - Steward: -

With **USB-Root**, the root directory (`/`) can be moved to a USB device
connected to the Fritz!Box, creating additional space not only for more
software.

### Advantages

-   A runnable system is still available in the Fritz!Box flash memory as
    an emergency system.
-   Almost unlimited space.
-   Several systems can be available in parallel on the USB stick, making
    it easy to test new versions and configurations. However, the AVM
    firmware base used in each case should have mutually compatible
    configuration formats.

**A practical example:**

Annex A box in France with a clueless user as owner ;-). If the system in
flash did not work, nothing would work anymore. But switching off the
power, removing the USB stick, and switching the power back on is still
manageable, allowing the emergency system in flash to be used.

### Configuration and Compilation

USB-Root simply has to be selected when creating the image with
`make menuconfig` (see [Freetz Installation?]). To have a shell on the
Fritz!Box later and be able to use scp, dropbear should also be included
in the image. First, an image with USB-Root is created that fits into the
Fritz!Box flash memory and is then flashed to the Fritz!Box like any
other image.

Then the system for USB-Root can be assembled without having to worry
about space anymore. However, the USB-Root package must remain selected.
The error message at the end saying that the image is too large is not a
problem here. Only the created system is needed, which can be found in
[Freetz folder]/build/modified/filesystem.

Any Freetz version can be used for the USB stick. It does not have to be
the same version as the one stored in the Fritz!Box flash memory. Only
the kernel in flash memory must match the kernel on the USB stick.

Use a partition with ext2 or ext3 as the filesystem. The matching kernel
module must be selected when creating the image.

### Pack, Copy to the Fritz!Box, and Unpack

```
# 1. Pack the filesystem, changing owner to root:root
tar --group=0 --owner=0 -czf rootfs.tar.gz -C build/modified/filesystem .

# 2. Disable USB-Root in the Freetz web interface if it is already active

# 3. Restart the box with firmware from flash

# 4. Copy the archive directly to a USB medium connected to the box (adjust target path!)

# Variant A: push the file from the PC to the box (requires SSH server on the box)
scp rootfs.tar.gz root@fritz.box:/var/media/ftp/uStor01/rootfs

# Variant B: fetch the file from the PC on the box (requires SSH server on the PC)
scp user@my_pc:/home/user/freetz-trunk/rootfs.tar.gz /var/media/ftp/uStor01/rootfs

# 5. Unpack the archive on the box
cd /var/media/ftp/uStor01/rootfs
tar -xzf rootfs.tar.gz

# 6. If USB-Root has not been used yet, configure it first in the Freetz web interface (select partition and enter directory, for example /rootfs)

# 7. Enable USB-Root in the Freetz web interface, restart the box from USB-Root
```

**New in the development version since Changeset r8566:**
It can be configured directly in *Menuconfig* that, during the build, the
filesystem is packed directly into an archive in addition to or instead
of the firmware image ("USB Root Mode", replacing step 1 above).
Alternatively, "NFS Root Mode" also makes it possible to copy the
filesystem directly, fully unpacked, to the USB stick (steps 1, 3, 4), as
long as it is connected to the PC or reachable via NFS. The first variant
is probably the more common one and looks like this:

```
### Freetz Configuration

[*] Show advanced options
--> Advanced options
    --> Build system options
        --> Firmware packaging (fwmod) special options
            [*] Skip packing modified firmware
            [*] Pack file system into archive (USB root mode)
```

### Mounting Partitions

Mounting additional partitions did not work in early Freetz versions, so
these partitions had to be mounted manually. In current Freetz versions,
this now works, so the AVM features that store data on USB partitions can
be used.

However, when mounting the partitions, there is an error message for the
root partition being used: since it is already mounted, another mount
attempt (the "normal" one from AVM) naturally fails. This can safely be
ignored.

### Possible Side Effects

The Freetz usbroot package changes the environment variable kernel_args
and starts an alternative init process there
(init=/etc/init.d/rc.usbroot). The variable kernel_args1 is also set.
During a firmware upgrade or recovery, this can cause problems; therefore
the **usbroot function MUST be disabled again before the firmware update
or recovery, either through the Freetz web interface or from the shell
with:**

```
echo kernel_args > /proc/sys/urlader/environment
echo kernel_args1 > /proc/sys/urlader/environment
```

If this is noticed too late, for example the box restarts after only 5
seconds, the ADAM2 commands help:

```
quote SETENV kernel_args
quote SETENV kernel_args1
```

If it still does not help after the two commands, perform a recovery and
then flash a Freetz **without any extras** (without packages and
**without** usbroot) to the box via the AVM web interface, set the two
variables back to their normal value (via Telnet), and then the desired
modified firmware can be put on the box again without problems.

### Possible Improvements

1.  Copy directly to the Fritz!Box from the Stinky VM via SCP or rsync.
    If the Fritz!Box can be reached directly from the build system (for
    example a VM with Stinky) over the network via ssh/scp, the detour
    through another PC is unnecessary. In that case, a direct connection
    between Fritz!Box and build system would be more elegant. The variant
    above is still useful for remote systems without externally reachable
    SSH access.
2.  Put the repeated commands into a bash script.

