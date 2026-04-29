# clonezilla 5.15.23 (script bundle)
  - Homepage: [https://clonezilla.org/](https://clonezilla.org/)
  - Manpage: [https://clonezilla.org/clonezilla-live.php](https://clonezilla.org/clonezilla-live.php)
  - Changelog: [https://github.com/stevenshiau/clonezilla/tags](https://github.com/stevenshiau/clonezilla/tags)
  - Repository: [https://github.com/stevenshiau/clonezilla](https://github.com/stevenshiau/clonezilla)
  - Package: [master/make/pkgs/clonezilla/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/clonezilla/)
  - Steward: -
  - Additional documentation: https://clonezilla.org/

clonezilla is installed as a DRBL script bundle under /usr/share/drbl,
with wrapper commands in /usr/sbin:

- clonezilla
- ocs-sr
- ocs-onthefly

## How to run clonezilla

1. Connect to the box via SSH.
2. Check that wrappers are available:
   - which clonezilla
   - which ocs-sr
3. Start interactive mode:
   - clonezilla
4. For non-interactive/advanced usage, run upstream tools directly:
   - ocs-sr --help
   - ocs-onthefly --help

## Notes

- This package provides scripts only; cloning reliability depends on the
  selected filesystem/image tools and your storage topology.
- Typical dependencies selected by this package include partclone,
  udpcast, ddrescue, fsarchiver and ntfs/ntfsclone support.
