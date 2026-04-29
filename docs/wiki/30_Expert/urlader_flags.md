# Store Settings in the Urlader Environment

### Foreword and Motivation

It can be useful to query certain switches, or flags, during the boot
process or possibly afterwards without immediately having to access
`/var/flash/debug.cfg`. There are several reasons for this:

-   The character devices under `/var/flash` are available only after
	`/etc/init.d/rc.S` has run, because they are created in that script
	with `mknod`. In particular, `debug.cfg` is created separately only at
	the end of the script.
-   We would like to call certain functionality ***before*** `rc.S` runs.
	The best example is root mounts, such as the Freetz package `mini_fo`,
	whose init script registers itself in `/etc/inittab` before `rc.S`. If
	we wanted a switch to prevent loading `mini_fo`, we would have a
	problem.

### Possible Solutions

No problem without a solution. Inside `rc.mini_fo` itself, we could use
`mknod` to make `debug.cfg` temporarily accessible, then clean up with
`rm` after querying the desired information so that `rc.S` is not confused
later when creating the node again. There is in fact a package,
NFS-Root, that uses this technique to access AVM configuration data from
the TFFS. It also obtains information from another place: the so-called
bootloader environment, the Urlader environment variables. Since 15.0,
two still-undocumented DS-Mod logging tools, Inotify Tools and
*Dmesg Recording*, also access these environment variables. The latter two
even do so through a small shell API I came up with, functionally limited
to certain use cases. More about that later.

### Bootloader Environment

The Urlader, English bootloader, also known depending on version as ADAM2
or EVA, has a so-called environment, a small storage area for global
settings that are absolutely required for the box to work at all. This is
well known, but as a refresher here is the output generated on my 7170
with kernel 2.6, anonymized with `#`:

```
	$ cat /proc/sys/urlader/environment
	HWRevision      94.1.1.0
	ProductID       Fritz_Box_7170
	SerialNumber    0000000000000000
	annex   B
	autoload        yes
	bootloaderVersion       1.153
	bootserport     tty0
	bluetooth       ##:##:##:##:##:##
	cpufrequency    211968000
	firstfreeaddress        0x946AE530
	firmware_version        1und1
	firmware_info   29.04.29
	flashsize       0x00800000
	maca    ##:##:##:##:##:##
	macb    ##:##:##:##:##:##
	macwlan ##:##:##:##:##:##
	macdsl  ##:##:##:##:##:##
	memsize 0x02000000
	modetty0        38400,n,8,1,hw
	modetty1        38400,n,8,1,hw
	mtd0    0x90000000,0x90000000
	mtd1    0x90010000,0x90780000
	mtd2    0x90000000,0x90010000
	mtd3    0x90780000,0x907C0000
	mtd4    0x907C0000,0x90800000
	my_ipaddress    192.168.178.1
	prompt  AVM_Ar7
	ptest
	reserved        ##:##:##:##:##:##
	req_fullrate_freq       125000000
	sysfrequency    125000000
	urlader-version 1153
	usb_board_mac   ##:##:##:##:##:##
	usb_rndis_mac   ##:##:##:##:##:##
	usb_device_id   0x3D00
	usb_revision_id 0x0200
	usb_device_name USB DSL Device
	usb_manufacturer_name   AVM
	wlan_key        ################
	wlan_cal        ####,####,####,####,####,####,####,####,####
```

The nice thing about this environment is that it is not only readable but
also partly writable. This is often used to adjust annex or branding,
especially on OEM boxes whose owners want to turn them into full
FRITZ!Boxes in order to install the corresponding original firmware or
Freetz, or to make a German box work abroad or vice versa.

For most values in the environment, abusing them for other purposes is
absolutely not advisable. But there is a variable, not visible above, that
was created to pass parameters to the Linux kernel for the boot process.
These parameters are later passed on to the startup scripts and are also
stored persistently, making them ideally suited for querying values from
there.

### The `kernel_args` Variable

The variable discussed here is called `kernel_args`. It holds at most 64
characters of information and should therefore be used carefully. You can
write something into it like this:

```
    echo "kernel_args tea=Darjeeling quality=FTGFOP1" > /proc/sys/urlader/environment
```

This would instruct a specially designed, unfortunately fictional,
FRITZ!Box startup script to brew tea while the box boots, specifically
Darjeeling of quality grade FTGFOP1, Finest Tippy Golden Flowery Orange
Pekoe 1.

If you display the environment again now, the variable `kernel_args`
suddenly appears there:

```
    $ cat /proc/sys/urlader/environment | grep kernel_args
    kernel_args     tea=Darjeeling quality=FTGFOP1
```

With a bit of string manipulation, we can isolate the value of
`kernel_args` and then split it further into our two key-value pairs. I
will not go into this further here; it is basic shell programming.

It is important, however, to know how to access this variable during the
boot process. The answer depends on the point in time when access is
needed. If the virtual filesystem under `/proc`, the so-called *procfs*,
is already accessible and has therefore already been mounted into the root
filesystem with `mount`, we can proceed as shown above. Otherwise, we must
first mount *procfs* ourselves with:

```
    [ -e /proc/mounts ] || mount proc
```

After use, it can be removed again with `umount proc`.

### Kernel_Args API

For simple use cases focused on debugging or logging that can make do
inside `kernel_args` with the values:

-   active/yes,
-   inactive/no,
-   countdown counter \> 0,

there is the shell script `kernel_args`. It can be included in a running
script with `. /usr/bin/kernel_args`, after which several ready-made
functions are available to manipulate key-value pairs stored inside the
bootloader variable `kernel_args`. The script is well documented in its
comments, so here is only a short list of functions currently available
in ds26-15.2:

-   **ka_mountProc:** mount `/proc` if necessary
-   **ka_getArgs:** read the complete `kernel_args`
-   **ka_getKeyValuePair:** determine the key-value pair for a given key
-   **ka_isValidName:** check key names for validity
-   **ka_isValidValue:** check value validity, `y`, `n`, or number \> 0
-   **ka_getValue:** determine the value for a key
-   **ka_setValue:** set the value for a key
-   **ka_removeVariable:** delete a key-value pair
-   **ka_removeVariableNoUpdate:** as above, but only display the new
	value of `kernel_args` after assumed removal of a pair, without
	writing directly to the environment
-   **ka_isPositiveInteger:** helper function to check numeric values
-   **ka_isActiveVariable:** check whether the value is \> 0 or `y`, active
-   **ka_decreaseValue:** reduce a positive integer value by 1. If it
	would become 0, replace the value with `n`, inactive

### Countdown Trick

The last two calls in particular enable a helpful construct when
developing startup scripts: set a variable to 5, for example, and reduce
it by 1 on each boot until it is set to `n`, inactive, after five runs.
Depending on that, the further course of a script could be influenced: it
could continue or terminate early. If an error occurs later in the script
that torpedoes the box startup so the box can no longer be reached without
recovery, this countdown is a practical aid. By the sixth attempt at the
latest, the faulty function would no longer be activated and the box would
continue booting normally. We are saving ourselves from ourselves here and
pulling ourselves out of the swamp by our own hair. ;-)

### Limits of the kernel_args API

As soon as we want to store other types of values in `kernel_args`, for
example something like `my_path=/usr/bin/my_script`, the current API no
longer helps because it allows only the values `y`, `n`, and positive
integers. But direct access, as shown above, can still handle this. Maybe
one day I will extend the API as well.

### Possible Use Cases

**Root mounts:** Services such as `mini_fo`, which virtually overlays the
root filesystem with a RAM disk or external storage to enable write
access, or *NFS-Root*, the complete replacement of the root filesystem
with a fully writable and practically unlimited network mount, could
benefit from switches in the bootloader environment because they could be
enabled and disabled as needed. Note: NFS-Root actually uses an entry in
`kernel_args` for enabling and disabling, though without the API. In
addition, the NFS path to be mounted is stored in another bootloader
variable named `nfsroot`, which the Linux kernel knows anyway and which we
more or less misuse.

**Debugging/logging:** Functions that can be enabled on demand to log file
accesses during boot, for example to determine which binaries are *not*
touched during startup and can therefore be outsourced through the
Downloader CGI to free space for DS-Mod packages needed earlier, or to
save the kernel log to a file before the ring buffer overflows and the
beginning is lost, are further sensible areas of use for `kernel_args`,
with or without the API. The developer does not need to flash a debug
version of the firmware to try something; instead, the necessary parts are
built permanently into the firmware, but their startup depends on one or
more switches considered in the init scripts. Very convenient.

Further mischief is left to your valued imagination.

Please discuss the topic at
[http://www.ip-phone-forum.de/showthread.php?t=134976](http://www.ip-phone-forum.de/showthread.php?t=134976),
where the beginning still talks about using the variable *SerialNumber*
to store values there. Later, however, it turned out that this variable
can apparently be changed, but the changes do not survive a box restart.
So do not be confused: the current state of the art is `kernel_args`.

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)


