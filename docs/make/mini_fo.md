# mini_fo 0.3 - DEPRECATED
  - Package: [master/make/pkgs/mini_fo/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/mini_fo/)
  - Steward: -

[![Mini_fo Webinterface](../screenshots/205_md.png)](../screenshots/205.png)

**mini_fo** is an overlay filesystem comparable to
[UnionFS](http://de.wikipedia.org/wiki/UnionFS), known from various live
distributions, for example Knoppix. Put simply, it can make a read-only
filesystem writable. Of
course, it is not possible to really (physically) write to the read-only
medium: changes are stored elsewhere, but this happens so transparently
for the user that they essentially do not notice it and really have the
impression of a single writable medium.

### Configuration (Web Interface)

The package is configured through the web interface. The storage location
for changes can be selected there: either RAM (volatile) or JFFS2
(reboot-resistant). If the JFFS2 option is selected, enough free space
must be available; the data is stored gzip-compressed:

```
root@fritz:/var/mod/root# df /dev/mtdblock5
Filesystem           1K-blocks      Used Available Use% Mounted on
/dev/mtdblock5            3200      2612       588  82% /sto
```

The package can only be deactivated or activated by rebooting.

### Configuration (Manually)

**mini_fo** is a kernel module that can either be loaded without
arguments using insmod...

```
 insmod mini_fo
```

...or entered under Modules in the Freetz interface so that it is loaded
at startup:

```
 mini_fo
```

Once it is active, the mount type 'mini_fo' is available. To make
/usr/www writable, this line in rc.custom is sufficient:

```
mkdir -p /tmp/usrwww /tmp/usrwww-sto && 
 mount -o bind /usr/www /tmp/usrwww && 
 mount -t mini_fo -o base=/tmp/usrwww,sto=/tmp/usrwww-sto minifo /usr/www
```

All changes are then located in the path /tmp/usrwww-sto.

### Possible Side Effects

A firmware update may fail with the mini_fo module loaded (tested with
7170 4.8x). There is then no error message, but the box hangs before
shutting down and the flashing process never happens. If this happens,
boot without mini_fo before a firmware update. Current trunk does not
show this phenomenon.

If mini_fo is operated on a box without a JFFS2 partition, it also
intercepts write accesses to /data, at least until a USB stick is
mounted. In /sto/mini_fo, data/tam/config and data/tam/rec/ then appear
with the date 2000, before time synchronization. This side effect makes
it possible to test answering machines without a JFFS2 partition and
without a USB stick, for example for forwarding by email followed by
deletion. The recording length should be limited so the RAM memory cannot
accidentally be exhausted. However, if mini_fo stores in RAM, all
answering machines defined in this way are lost on restart.

On 7170-generation models, watchdog-initiated reboot loops (about 2-4
minutes) occurred when WLAN encryption was enabled in DSL modem mode,
which is the default after a factory reset. The reboot reason in
crash.log is then a dsld watchdog timeout. Without WPA encryption or in
IP client mode, this phenomenon does not appear. Apparently, semaphores
that dsld stores in /var/tmp/csem to manage shared memory are partly
queried in /sto, sensitively disrupting the mechanism.

### Restore original file

The modified files are stored here (trunk version):

```
/sto/mini_fo/...
```

So for example a modified */usr/sbin/blkid* is stored as
*/sto/mini_fo/usr/sbin/blkid*.

If you remove the latter one, the original one will reappear in your
file system.

### Further Links

-   [this
  thread](http://www.ip-phone-forum.de/showthread.php?t=111226)
  in the forum.
-   [mini_fo project
    page](http://www.denx.de/twiki/bin/view/Know/MiniFOHome).

