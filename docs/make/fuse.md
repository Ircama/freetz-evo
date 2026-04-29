# FUSE 2.9.9 (binary only) - DEPRECATED
  - Homepage: [https://github.com/libfuse/libfuse](https://github.com/libfuse/libfuse)
  - Manpage: [https://github.com/libfuse/libfuse/wiki](https://github.com/libfuse/libfuse/wiki)
  - Changelog: [https://github.com/libfuse/libfuse/releases](https://github.com/libfuse/libfuse/releases)
  - Repository: [https://github.com/libfuse/libfuse/commits/master](https://github.com/libfuse/libfuse/commits/master)
  - Package: [master/make/pkgs/fuse/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/fuse/)
  - Steward: -

**[FUSE](http://de.wikipedia.org/wiki/Filesystem_in_Userspace)**
([Filesystem](http://de.wikipedia.org/wiki/Dateisystem)
in
[Userspace](http://de.wikipedia.org/wiki/Userspace))
is a
[kernel module](http://de.wikipedia.org/wiki/Kernel-Modul)
that makes it possible to move filesystem drivers out of
[kernel mode](http://de.wikipedia.org/wiki/Betriebssystemkern)
and into
[user mode](http://de.wikipedia.org/wiki/Ring_(CPU)). This allows
unprivileged users, meaning users who are not *root*, to mount or create
filesystems. The *FUSE* modules effectively act as a bridge to the kernel
interfaces.

*FUSE* is especially useful for implementing virtual filesystems. Unlike
traditional filesystems, which are responsible for storing and loading
data on disk, virtual filesystems do not store data themselves. Instead,
they are a view or translation of an already existing file or storage
system. In principle, any resource available to *FUSE* can be exported as
a filesystem.

In Freetz, for example, the [NTFS](ntfs-3g.html) package is based on
*FUSE*.

### Further Links

 - [Wikipedia: FUSE](http://de.wikipedia.org/wiki/Filesystem_in_Userspace)
 - s3fslite for Freetz: Ticket #796

