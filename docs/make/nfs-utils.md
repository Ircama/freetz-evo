# nfs-utils 1.3.4 (binary only) - DEPRECATED
  - Homepage: [https://sourceforge.net/projects/nfs/](https://sourceforge.net/projects/nfs/)
  - Manpage: [https://www.linux-nfs.org/](https://www.linux-nfs.org/)
  - Changelog: [https://sourceforge.net/projects/nfs/files/nfs-utils/](https://sourceforge.net/projects/nfs/files/nfs-utils/)
  - Repository: [http://git.linux-nfs.org/?p=steved/nfs-utils.git](http://git.linux-nfs.org/?p=steved/nfs-utils.git)
  - Package: [master/make/pkgs/nfs-utils/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nfs-utils/)
  - Steward: -

The NFS utils extend Freetz with an NFS server including an
administration web interface (see [nfsd-cgi](nfsd.md)) for the
configuration files `Exports`, `allow_hosts`, and `deny_hosts`.

### Notes

-   Exports work correctly only with ext2, ext3, or ReiserFS filesystems.
-   Squashfs and tmpfs/ramfs (/var) cannot be exported over NFS.
-   If no connection is established, this may be due to the wrong NFS
    version on the client. This can be fixed with the additional mount
    parameter `-o nfsvers=3`.

### References

-   [http://www.ip-phone-forum.de/showthread.php?p=1609992](http://www.ip-phone-forum.de/showthread.php?p=1609992)
-   [http://de.wikipedia.org/wiki/Network_File_System](http://de.wikipedia.org/wiki/Network_File_System)

