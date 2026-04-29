# NTFS-3G 2022.10.3 (binary only)
  - Package: [master/make/pkgs/ntfs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ntfs/)
  - Steward: -

NTFS-3G provides read/write NTFS support and NTFS userspace tools.

In this package:

- `FREETZ_PACKAGE_NTFS_DRIVER` installs the `ntfs-3g` mount binary.
- `FREETZ_PACKAGE_NTFS_TOOLS` enables the ntfsprogs tools set.

Selectable ntfsprogs tools include:

- `mkntfs`
- `ntfscat`
- `ntfsclone`
- `ntfscluster`
- `ntfscmp`
- `ntfscp`
- `ntfsfix`
- `ntfsinfo`
- `ntfslabel`
- `ntfsls`
- `ntfsresize`
- `ntfsundelete`

`ntfsclone` is commonly used by clone/imaging workflows (for example with
Clonezilla-related setups).

