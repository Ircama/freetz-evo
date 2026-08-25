# Add FREETZMOUNT
Assigns uniform names to USB storage media, significantly improves USB storage media support, and enables mounting by LABEL.
FREETZMOUNT is the successor to the USB-Storage patch and also includes the autorun/autoend patch.
After switching to FREETZMOUNT it is recommended to manually deselect the fstyp package.<br>
<br>

FREETZMOUNT is the successor patch to the former USB-Storage patch. In addition to the functions of the USB-Storage patch, it also includes the autorun/autoend functionality (configurable via the web interface).
FREETZMOUNT integrates deeper into the AVM mount structure than its two predecessor patches and moves parts of the mount scripts from /etc/hotplug/storage and /etc/hotplug/run_mount into Freetz's own library /usr/lib/libmodmount.sh. This reduces the maintenance effort for these patches and unifies the mount behavior for all box/firmware versions.
FREETZMOUNT enables mounting media by a so-called LABEL, a uniform designation for the media. This ensures that the medium (partition) will always be found under the same mount point (fighting the uStor11 problem).

Notes:

 * When selecting the "mount-by-label" feature, fstyp is no longer required and can be deselected: Package-Selection -> Testing -> fstyp.
 * Although it should actually be obvious, here again for clarification:

A program that is responsible for mounting in any way must not be externalized on a medium that is to be mounted.
This includes, for example, e2fsck, ntfs-3g and blkid.

Further information can be found, for example, in the following IP-Phone-Forum threads:

 * [FREETZMOUNT: Mounting without patching a thousand times](http://www.ip-phone-forum.de/showthread.php?t=200293)
 * [Modifying /etc/hotplug/run_mount](http://www.ip-phone-forum.de/showthread.php?t=200293)
 * [Script for always identical mount points (also after loss of the mount)](http://www.ip-phone-forum.de/showthread.php?t=181859)
