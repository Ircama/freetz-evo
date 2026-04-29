# Debootstrap (binary only) - DEPRECATED
  - Package: [master/make/pkgs/debootstrap/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/debootstrap/)
  - Steward: -

**Debootstrap** can be used to install a Debian system from scratch. This
can be done from a running system onto another partition or into a
directory on the current system, for example to test another Debian
release version. It is also possible to use *debootstrap* to install
Debian from another Linux distribution.

Initially, *Debootstrap* requires neither
[dpkg](http://de.wikipedia.org/wiki/Debian_Package_Manager)
nor [apt](http://de.wikipedia.org/wiki/Advanced_Packaging_Tool).
The initial system is created by downloading the Debian packages from a
mirror site and carefully unpacking them into a local directory, into
which one can finally [chroot](http://de.wikipedia.org/wiki/Chroot).

If *Debootstrap* is not yet installed, for example under Debian or
Ubuntu, it can be installed with:

```
sudo apt-get install -y debootstrap
```

### Use Debian in a Few Steps

First download the Debian system with Debootstrap. This can be done from
any other system that contains the Debootstrap program, for example also
from the freetzed box with the Debootstrap package selected. Otherwise,
the only requirement is that the mounted partition uses ext2, ext3, or
ext4 as its filesystem. Because there are often problems with the current
lenny Debian, etch is used here. It is recommended to run the first two
commands on the computer, as this is much faster. In this case,
*---foreign* should be added to the arguments. For all common FritzBox
models up to x2xx, enter *---arch=mipsel*; for current x3xx models,
enter *---arch=mips*.

**Note**:

The name of the connected USB device can vary. In the paths shown below,
the name is *uStor01*; for other devices it can also be
Generic-FlashDisk-01. There are 3 ways to find out the name: via the
[web interface](http://192.168.178.1/nas/index.lua) (FRITZNAS), FTP (the
root directory must be visible), or enabled Telnet.

**Telnet** (the USB device is listed in the overview)

```
ls /var/media/ftp/
```

**Output could look like this** (varies by model/firmware):

```
FRITZ-NAS.txt         FRITZ-Song.mp3        Generic-FlashDisk-01  lost+found
FRITZ-Picture.jpg     FRITZ-Video.mp4       Onlinespeicher
```

**Try with *Etch*** (outdated version):

(FritzBox models up to version x2xxx)

```
debootstrap --foreign --arch=mipsel etch /var/media/ftp/uStor01/debian http://ftp.de.debian.org/debian
```

(FritzBox models from version x3xxx)

```
debootstrap --foreign --arch=mips etch /var/media/ftp/uStor01/debian http://ftp.de.debian.org/debian
```

**Try with *Wheezy*** (current version):

(FritzBox models up to version x2xxx)

```
debootstrap --foreign --arch=mipsel wheezy /var/media/ftp/uStor01/debian http://ftp.de.debian.org/debian
```

(FritzBox models from version x3xxx)

```
debootstrap --foreign --arch=mips wheezy /var/media/ftp/uStor01/debian http://ftp.de.debian.org/debian
```

then

```
chroot /var/media/ftp/uStor01/debian /debootstrap/debootstrap --second-stage
```

If Debootstrap was run on another PC, insert the relevant USB stick into
the FritzBox now. To be able to use Debian now, the /proc/ directory must
be provided for Debian and, as already mentioned, chroot must be used:

```
mount -t proc proc /var/media/ftp/uStor01/debian/proc
chroot /var/media/ftp/uStor01/debian bash
```

If everything goes well, the following prompt should appear:

```
root@fritz
```

From now on, after an apt-get update, additional packages can be
installed as usual with apt-get install.

### Experience Values

The initial installation on a 7170 takes about 2 hours, with about 45/75
minutes distributed over the first 2 steps. The used storage space on an
EXT3-formatted data carrier is about 505 MB (March 2011). Unlike later
use, especially of Aptitude, the installation does not yet require swap,
but it does increase CPU usage to 100% during this time.

### Further Links

-   [Linux-Wiki:
    Debootstrap](http://www.linuxwiki.de/debootstrap)
-   [Debian user manual:
    Debootstrap](http://debiananwenderhandbuch.de/debootstrap.html)
-   [Installing new Debian systems with
    debootstrap](http://www.debian-administration.org/articles/426)
-   [IPPF thread about mail servers in Debian
    chroot](http://www.ip-phone-forum.de/showthread.php?t=169744)
-   [Debootstrap in the Wehavemorefun
    Wiki](http://wehavemorefun.de/fritzbox/index.php/Debootstrap)

#### Comment by oliver on Sat 26 Feb 2011 11:26:45 CET

Creating the Debootstrap is relatively simple and well described. But how
do you use it now? The proc mount can be written into rc.custom. And what
do you do with chroot? Can you create a screen session at startup and
then connect to it? Or enter the chroot command every time?

#### Comment by mandy28 on Sat 26 Feb 2011 13:09:38 CET

Start chroot from the console, or conveniently with an addon that is then
also responsible for the binary that should run in the chroot.

#### Comment by oliver on Tue 01 Mar 2011 21:09:47 CET

I have now installed debootstrap, but /etc/apt/sources.list is empty.
Could you describe what has to go in there so packages can be installed?

#### Comment by mandy28 on Tue 01 Mar 2011 22:30:28 CET

should look like this

```
deb http://ftp.de.debian.org/debian stable main
```

#### Comment by oliver on Tue 01 Mar 2011 22:43:32 CET

Should that already be in there, or do you have to write it yourself?

#### Comment by mandy28 on Tue 01 Mar 2011 22:54:33 CET

Normally it should already be in there like that or similarly.

#### Comment by MyRaCoLi on Wed 02 Mar 2011 02:55:27 CET

Does this work with the current stable, squeeze? Lenny is still listed
here incorrectly as stable.

#### Comment by mandy28 on Wed 02 Mar 2011 08:15:05 CET

With the corresponding scripts in debootstrap, yes, but then through a
different mirror, for example:

```
debootstrap --foreign --arch=mipsel squeeze /var/media/ftp/uStor01/squeeze http://ftp.de.debian.org/debian
chroot /var/media/ftp/uStor01/squeeze /debootstrap/debootstrap --second-stage
```

#### Comment by kriegaex on Mon 12 Dec 2011 23:05:51 CET

After creating Debootstrap on the PC and copying it to the 7170 via NFS,
I only get the following error message when chrooting:
"FATAL: kernel too old"

#### Comment by zocky on Thu 26 Jul 2012 18:43:38 CEST

About this too-old fb kernel problem: with 7170 firmware version 29.04.76,
I also had the message "FATAL: kernel too old" with everything higher
than etch, so you simply have to take an older distribution until it
works.

The sources.list may then have to be adjusted to archive servers. In my
case this currently works with these entries:

```
deb http://archive.debian.org/debian-archive/debian/ etch main contrib
non-free
deb-src http://archive.debian.org/debian-archive/debian/ etch main
contrib non-free
```

But this can change depending on the distribution and the current time.

[AddComment?]
