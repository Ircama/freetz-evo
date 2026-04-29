# Back Up Flash Partitions Externally with FTP

This article builds on the article about flash partitioning. Reading it
first will not hurt. My heartfelt thanks for some of the information in
this article go to Enrik Berkhan, who always keeps a low profile here but
knows so much. :-)

### Motivation

In the related article "Back up flash partitions while running", I
explained how to create backups directly from the FRITZ!Box console, via
SSH, Telnet, or Rudi shell, using the corresponding Linux block or
character devices. The same can also be done "from outside", without
shell access on the box, by contacting the Urlader, in modern terms the
bootloader, via FTP. The Urlader used to be called ADAM2; in current
kernel 2.6 firmware it is called EVA, although the login data is still the
same as before, as we will see shortly.

This method can also be used if the box no longer boots cleanly, if there
is no Telnet access on the box with original firmware, or if enabling
Telnet fails.

### Requirements

We need a FRITZ!Box with kernel 2.6 and EVA Urlader, because with older
versions the FTP commands may have changed more or less significantly. I
do not know that exactly. A corresponding OEM device also works, for
example Speedport W501V, W701V, or W900V.

In addition, we need a **Linux** system, also possible as a virtual
machine such as VMware, with the standard command-line client `ftp`
installed, in my case Debian package `ftp 0.17-16`, or with
[NcFTP](http://en.wikipedia.org/wiki/Ncftp) 3.2.0, in my case Debian
package `ncftp 2:3.2.0-1`.

Alternatively, the described procedure with NcFTP 3.2.0 also works under
**Windows with Cygwin**. There it does not work with the standard FTP
client, and certainly not with Windows FTP.

The boot IP of the box should also be known. If it is unknown and no
information can be obtained from the box through a console, SSH, Telnet,
Rudi shell, or nano shell, it can be found with `ping` by pinging
different IP addresses immediately after switching the box off and on, or
unplugging and reconnecting it. These IPs are often used:

-   192.168.178.1 (allermeistens)
-   169.254.1.1
-   192.168.2.1
-   192.168.2.254

The normal and simple method to find the boot IP is this:

```
	cat /proc/sys/urlader/environment | grep my_ipaddress
```

Make sure personal firewalls are disabled, and possibly other security
packages that could interfere with network traffic as well. If it does
not work while such programs are active, disable them at the latest then,
even if you believe everything is configured correctly and they cannot be
the cause. Disable them completely, not just set them inactive.

It is also helpful if the computer from which you try the pings and start
the FTP connection is in the same subnet as the box, for example
192.168.178.0/24 or netmask 255.255.255.0, with respect to the address
being tested. The fact that ping works from Windows does not necessarily
mean that a connection also works from VMware. Really test from the place
where you intend to work later.

Connection attempts may require several tries. If a ping or FTP connect
has not worked three or four seconds after switching on the box, it is
best to switch it off and on again until ping or FTP connect works. Under
Windows, it may also be necessary to disable Media Sensing by saving the
following as a text file named `mediasensing-aus.reg` and double-clicking
it to add it to the Windows registry:

```
	Windows Registry Editor Version 5.00

	[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\Tcpip\Parameters]

	"DisableDHCPMediaSense"=dword:00000001
```

A Windows restart may be needed after disabling it. AVM's recovery tool
does that, at least, but perhaps it also works without restarting. Media
Sensing can remain permanently disabled as long as the computer is not
constantly plugged into and unplugged from different networks where Media
Sensing is needed for different DHCP servers, for example a notebook used
alternately in the office and at home. If you do want to enable it again,
use this:

```
	Windows Registry Editor Version 5.00

	[HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\Tcpip\Parameters]

	"DisableDHCPMediaSense"=dword:00000000
```

### General Backup Information

The procedure shown below is always the same, even when different command
line clients are used. The whole process can also be done manually in the
FTP client dialog, and besides the clients named here, several others
will probably work. They should support passive data transfer, though, and
I do not give any guarantees anyway. ;-) The programs I tested should make
success much more likely.

There is one oddity to point out right away: after downloading each `mtd`
partition, you must manually press Ctrl-C once at the FTP client's command
line so the client continues or terminates. For some reason, the end of a
GET download is not detected, probably because of the Urlader. It is best
to check in a second console on the client whether the download file is
still growing. After a few seconds it should no longer do so. The Urlader
and TFFS partitions are downloaded almost instantly anyway; only `mtd1`,
the partition for kernel plus filesystem of the box, takes a little
longer, but still completes quickly. These file sizes apply:

-   Filesystem + kernel (`mtd1`):
    -   7.616 KB = 7.798.784 bytes on 8 MB boxes
    -   3.520 KB = 3.604.480 bytes on 4 MB boxes
    -   1.472 KB = 1.507.328 bytes on 2 MB boxes; theoretical, these
        boxes currently still have old Urladers
-   Urlader/bootloader/EVA (`mtd2`): always 64 KB = 65.536 bytes
-   TFFS1 (`mtd3`): always 256 KB = 262.144 bytes
-   TFFS2 (`mtd4`): always 256 KB = 262.144 bytes

The sum of `mtd1-4` is always exactly 8, 4, or 2 MB, matching the memory
size of the respective box.

### Backup with Linux Standard FTP (`ftp`)

Because of the multiple lines, it is best to put the following code into a
script file and run it from there. Enter the appropriate IP address and,
after each partition has fully downloaded, press Ctrl-C once so the next
partition is downloaded, or so the FTP session is ended at the end.

```
    (
    cat <<EOT
    open 192.168.178.1
    user adam2 adam2
    debug
    bin
    quote MEDIA FLSH
    get mtd1
    get mtd2
    get mtd3
    get mtd4
    quit
    EOT
    ) | ftp -n -p
```

Afterwards, the current directory should contain four files, `mtd1` to
`mtd4`.

### Backup with Linux NcFTP (`ncftpget`)

Replace the IP address here as well. Run the script once for each of the
four partitions from `mtd1` to `mtd4`; all at once does not work here.
Ctrl-C at the end of the download is also required here to finish.

```
	ncftpget \
		-d stdout \
		-o doNotGetStartCWD=1,useFEAT=0,useHELP_SITE=0,useCLNT=0,useSIZE=0,useMDTM=0 \
		-W "quote MEDIA FLSH" \
		-u adam2 \
		-p adam2 \
		ftp://192.168.178.1/mtd1
```

### Backup with Cygwin NcFTP (`ncftpget`)

This works the same way as under Linux with the application of the same
name; see above.

### Uploads via FTP

Analogously, uploads can also be done with `ftp` or `ncftpput`. Normally,
however, this should only be done for `mtd1`, kernel plus filesystem. For
that, ds26-15.2 already provides the convenient script
`tools/push_firmware.sh`; starting with 15.3 the `.sh` extension is
omitted. It runs under Linux and Windows + Cygwin and does exactly that.

The double-buffered TFFS, where firmware settings from both the
manufacturer and Freetz are stored, should only be restored in an
emergency and only to exactly the box from which it came, because it
contains part of the box identity. This has become somewhat less critical
since the transition from ADAM2 to EVA because the most important part of
the data moved directly into the bootloader; see
[Enrik's article about EVA](http://wehavemorefun.de/fritzbox/index.php/EVA).
Nevertheless, handle it carefully.

What has become much more sensitive is overwriting the Urlader, because
since the transition to EVA it contains truly important box-specific data.
In addition, it cannot be overwritten via FTP anyway because it is active
during the FTP session. The ADAM bootloader article describes how the
Urlader can be overwritten directly during operation from the console on
the box, but it does not explain how to get the box-specific data into the
image. It should therefore already be there, or one should examine the
update procedure from the original firmware, for example 06.04.33, which
contains a bootloader together with an update program, and read Enrik's
article mentioned above.

**I can only very strongly advise against overwriting the Urlader; it
should never be necessary!!!**


[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)


