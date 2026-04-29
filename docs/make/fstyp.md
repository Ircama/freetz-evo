# fstyp 0.1 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/fstyp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/fstyp/)
  - Steward: -

**fstyp** allows a user to determine the filesystem type of a mounted
or unmounted filesystem.

In Freetz, fstyp is used by freetzmount to detect the filesystem and
mount it correctly.
Note: when the "mount-by-label" option is used, all of this is handled
by **blkid** instead, making fstyp unnecessary for this purpose. The
drawback is that the image becomes several kilobytes larger.

