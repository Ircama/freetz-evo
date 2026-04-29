# Structure of a Patch

A patch is a text-format file, usually with the extension `.patch`
sometimes `.diff`, containing a list of differences between two versions
of a file. Patches contain only differences in text files. Differences in
binary files cannot be patched.

At the beginning of a patch there may be a comment describing where the
patch comes from, who contributed to it, which problem it solves, and so
on. The actual beginning of the differences is marked by `---`. Usually,
a patch contains three lines of context before and after each changed
line. These serve as a reference so the patch can still be applied even if
the file to be patched has changed and the line numbers are no longer
correct.

```
This patch is an example and adds a new entry to menuconfig.

Index: make/Config.in
===================================================================
--- make/Config.in   (Revision 7307)
+++ make/Config.in   (Arbeitskopie)
@@ -51,6 +51,7 @@
 source make/netcat/Config.in
 source make/nc6/Config.in
 source make/netsnmp/Config.in
+source make/newpackage/Config.in
 source make/nfs-utils/Config.in
 source make/ntfs/Config.in
 source make/openntpd/Config.in
```

In most cases, the two file names, here `make/Config.in`, are the same.
Sometimes they differ by extension, for example `.orig`, depending on how
the patch was created. The example therefore describes a change to
`make/Config.in`. Specifically, a new package named *newpackage* was
written and should now be added to menuconfig. The fifth line of the patch
contains information about where the section to be patched, the hunk, is
located in the file and how many text lines the patch changes. In the
example, the patch starts at line 51 and adds one line, `7-6=1`, marked by
`+`. The same result could be achieved by opening `make/Config.in` in a
text editor and adding the line `source make/newpackage/Config.in` at the
described location.

### Creating a Patch

If you changed a file, `Config.in`, diff it against SVN:

```
 svn diff Config.in > Config.patch
```

All changes in the directory and subdirectories:

```
svn diff > all.patch
```

If new files were created, they must first be added to SVN:

```
svn add file-or-directory-name
```

### Apply or Revert a Patch

Apply a patch:

```
$ patch -p0 < Config.patch
patching file Config.in
$
```

Revert a patch:

```
$ patch -Rp0 < Config.patch
patching file Config.in
$
```

If you see something like this:

```
$ patch -p0 < Config.patch
patching file Config.in
Hunk #1 FAILED at 1.
1 out of 1 hunk FAILED -- saving rejects to file Config.in.rej
```

then the patch no longer fits and must be renewed.

-   TODO, possibly copy from the
    [ippf-Wiki](http://wiki.ip-phone-forum.de/software:ds-mod:howtos#patches_in_den_ds-mod_einspielen)
    .

### How Do I Find the Place to Patch?

The primary answer to this question is: it depends on what it is about.
Because that is not very satisfying in the wiki, here are a few tips from
RalfFriedl using the concrete example of `crond` and its frontend, the
crontab window in the Freetz WebGUI.

Because cron is not a separate package but belongs to the Freetz base
system, the files for cron are under `make/mod/root/files`. If it were a
separate package, for example `inetd`, the files would be under
`make/inetd/files/root`.

The following explains how to change the crontab web interface and then
patch it. The easiest way to find the file is to search for text that
hopefully occurs rarely elsewhere. `crontab` seems to be a good value
here.

```
$ grep -r crontab make 2> /dev/null | fgrep -v /.svn/
make/mod/files/root/etc/init.d/rc.crond:        cat /tmp/flash/mod/crontab /etc/cron.d/* /tmp/cron.d/* 2> /dev/null |
make/mod/files/root/etc/init.d/rc.crond:            crontab -u root -
make/mod/files/root/etc/init.d/rc.crond:                [ -r /tmp/flash/crontab.save ] && mv /tmp/flash/crontab.save /tmp/flash/mod/crontab
make/mod/files/root/etc/init.d/rc.crond:                modreg file mod crontab 'crontab' 0 "crontab"
make/mod/files/root/etc/init.d/rc.crond:                modunreg file mod crontab
make/mod/files/root/etc/default.mod/crontab.def:CAPTION='Freetz: crontab'
make/mod/files/root/etc/default.mod/crontab.def:CONFIG_FILE='/tmp/flash/mod/crontab'
```

Searching in `make` is only necessary if you are not sure which directory
contains the files. If you know that cron belongs to the base system, you
can search directly in `make/mod/files`, which is faster. The redirection
`2> /dev/null` suppresses error messages caused by missing files or links.

Results in files with `/.svn/` in the path are not relevant here.

The text `crontab` occurs in the files `rc.crond` and `crontab.def`. That
does not yet tell us what needs to be done to add help to the page. So we
search for `Hosts`, because the Hosts page already has help text.

```
$ grep -r Hosts make 2> /dev/null | fgrep -v /.svn/
...
make/mod/files/root/etc/default.mod/hosts.def:CAPTION='Freetz: hosts'
root/etc/init.d/rc.mod:         modreg file 'exhosts' 'Hosts' 1 "$deffile"
... and many other matches
```

The definition file from which the text `hosts` comes is therefore
`make/mod/files/root/etc/default.mod/hosts.def`. So let us look at the
file:

```
$ cat make/mod/files/root/etc/default.mod/hosts.def
CAPTION='Freetz: hosts'
DESCRIPTION='Syntax: &lt;ip&gt; &lt;mac&gt; &lt;interface&gt; &lt;host&gt; [&lt;aliases|#description&gt;]<br>
($(lang de:"z.B.: 10.0.0.1 * * www.local mfh1 # Mein Server" en:"e.g. 10.0.0.1 * * www.local mfh1 # my server")) *=&quot;$(lang de:"nicht definiert" en:"not defined")&quot;'
... the rest is not relevant here
```

We can see that the description comes from the `DESCRIPTION` entry, which
is not present in `make/mod/files/root/etc/default.mod/crontab.def`. So a
`DESCRIPTION` entry must be created in
`make/mod/files/root/etc/default.mod/crontab.def`.

If multiple languages should be supported with `$(lang ...)`, make sure
the file is also listed in the appropriate list. This is the `.language`
file in the directory `make/<package>/files`.

The file looks like this:

```
$ cat .language
languages
{ de en }
default
{ en }
files
{
        etc/default.mod/*.def
        etc/init.d/rc.mod
        usr/bin/modreg
        ...
}
```

Here we can see that all files `etc/default.mod/*.def` are already
included and no further entry is necessary.

In this case, the only changed file is
`make/mod/files/root/etc/default.mod/crontab.def`; continue as described
below.

Background information can be found in this
[IPPF-Thread](http://www.ip-phone-forum.de/showthread.php?p=1274104#post1274104).

### Links

[Wikipedia article about diff](http://en.wikipedia.org/wiki/Diff)
[Wikipedia article about patch](http://en.wikipedia.org/wiki/Patch_(Unix))


