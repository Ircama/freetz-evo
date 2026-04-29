# inotify-tools 3.14 (binary only) - DEPRECATED
  - Homepage: [https://github.com/inotify-tools/inotify-tools](https://github.com/inotify-tools/inotify-tools)
  - Manpage: [https://github.com/inotify-tools/inotify-tools/wiki](https://github.com/inotify-tools/inotify-tools/wiki)
  - Changelog: [https://github.com/inotify-tools/inotify-tools/releases](https://github.com/inotify-tools/inotify-tools/releases)
  - Repository: [https://github.com/inotify-tools/inotify-tools/commits/master](https://github.com/inotify-tools/inotify-tools/commits/master)
  - Package: [master/make/pkgs/inotify-tools/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/inotify-tools/)
  - Steward: -

**Inotify** is a kernel interface for monitoring file accesses, combined
with an event mechanism that can notify you about certain events. See the
[German short](http://de.wikipedia.org/wiki/Linux_%28Kernel%29#Inotify)
and [English detailed](http://en.wikipedia.org/wiki/Inotify) Wikipedia
articles.

### Inotify and Inotify-Tools in General

The **[Inotify-Tools](http://inotify-tools.sourceforge.net)** are a small
collection of tools and programming interfaces that make it easier to use
this powerful mechanism. As a Freetz package, we provide two executable
tools and one library, namely

-   inotifywait,
-   inotifywatch and
-   libinotifytools

Usage examples are also available on the
[Sourceforge project page](http://inotify-tools.sourceforge.net/#info).
**Inotifywait** waits for an event for which it was previously registered
and returns when it occurs. This can also run in the background if events
should be monitored not just once, but continuously. **Inotifywatch**, on
the other hand, collects and summarizes statistical data about filesystem
events and provides them in tabular text form.

### Observe FritzBox File Accesses Starting at Boot

A special application, for which the startup script `rc.S` is prepared by
a special always-built-in patch, is logging all filesystem accesses when
the box starts. `rc.S` is the first script executed by `init`, meaning the
logging really starts very early, directly after the watchdog starts, so
nothing important is missed. Since it makes no sense to perform this
logging every time, it can be switched on and off. The [kernel_args-API?]
is used for this. Before the boot process to be logged, that is before
rebooting, activate logging:

```
# Load API
. /usr/bin/kernel_args
# Activate (attention, no "=", two parameters!)
ka_setValue InotifyBootAnalysis y
# Check whether variable is set
ka_getArgs
# Result e.g. idle=4 foo=bar InotifyBootAnalysis=y
```

Instead of the value "y", a positive integer value can also be assigned;
it is automatically decreased by 1 at each boot until it finally becomes
0, which leads to the follow-up value "n" and automatic deactivation of
the function. This first prevents forgetting deactivation permanently and
second eliminates possible problems during box startup caused by logging:
simply restart often enough until the function is inactive again.

The function can also be deactivated manually by replacing one line in
the code sequence above:

```
# Deactivate
ka_setValue InotifyBootAnalysis n
```

The variable can also be deleted completely from the bootloader
environment:

```
# Delete variable completely
ka_removeVariable InotifyBootAnalysis
```

Once logging has been started, it continues running until it is manually
stopped after the startup process is complete, or even later after as
much as desired has been logged. It could be useful to continue observing
the box for a few hours or days beyond startup to determine which files
are used at all, or not used, so they can then be outsourced and loaded
on demand in conjunction with the [Downloader-CGI](downloader.md), or
removed entirely from the firmware to make room for more or larger
packages. This is an art in itself, especially on boxes with only 4 MB of
flash. The 8 MB boxes are less constrained, but it can still be
interesting there if one suffers from "featuritis".

So how do you stop logging before memory fills up?

```
# Stop logging
/etc/init.d/rc.inotify_tools stop
```

Whether logging is currently running can be determined like this:

```
# Check status ("running" or "stopped")
/etc/init.d/rc.inotify_tools status
```

It is also possible at any time during operation to enable logging in
order to observe all file accesses at runtime if needed:

```
# (Re)start logging
/etc/init.d/rc.inotify_tools start
```

Attention, a small excursion into the more technical side: one should
know that `rc.inotify_tools start` briefly stops any logging that may
already be running and then immediately restarts it. This is somewhat
unusual, but can be useful in situations where init is ended by a script,
for example because of `kill -1 1` as used by `rc.mini_fo` to set up its
overlay filesystem in several passes, then started again and calls the
startup scripts once more. In between, logging may either still be
running or may have been aborted. In any case, Inotify-Tools starts again
in this situation, possibly now with output to the freshly mounted
*mini_fo* (previously to the now covered underlying filesystem).

### What Does rc.inotify_tools Log?

We could log everything, but that would be a large amount of data because
certain accesses, for example to frequently used files such as `busybox`,
`uClibc`, or `libcrypt`, would fill the log. That they are used should be
obvious anyway, and we certainly will not outsource them from the
firmware. So they are not considered during logging. This is what the
section in `rc.S` looks like where logging is started:

```
echo "starting inotifywait"
inotifywait -c -r -m / 
@/dev @/proc @/var @/rom @/sto 
--exclude 'busybox|uClibc|libcrypt-0' 
>> /var/iw.log 2> /dev/null &
sleep 3
```

It is therefore logged continuously and recursively, everything starting
from the root directory ("/" as the parameter at the end of the first
invocation line). Excluded are the virtual directories or directories
used for internal *Mini_fo* purposes: `/dev`, `/proc`, `/rom`, `/sto`,
and the RAM disk `/var`. Also excluded are files containing the strings
"busybox", "uClibc", or "libcrypt-0"; the "-0" at the end distinguishes
`libcrypt` from `libcrypto`.

The log is written to the RAM disk at `/var/iw.log`; "iw" stands for
"inotifywait".

### Output Format

What is in `/var/iw.log`, and what does it look like? A small excerpt:

```
/etc/,"CLOSE_NOWRITE,CLOSE",.subversion
/lib/,"CLOSE_NOWRITE,CLOSE",libgcc_s.so.1
/lib/,"CLOSE_NOWRITE,CLOSE",libgcc_s.so.1
/lib/,OPEN,libgcc_s.so.1
/lib/,ACCESS,libgcc_s.so.1
/lib/modules/2.6.13.1-ohio/modules/,DELETE_SELF,
/lib/modules/2.6.13.1-ohio/modules/,IGNORED,
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avm_event/,DELETE_SELF,
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avm_event/,IGNORED,
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avalanche_led/,DELETE_SELF,
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avalanche_led/,IGNORED,
/lib/,"CLOSE_NOWRITE,CLOSE",libgcc_s.so.1
/usr/share/images/,OPEN,edge_lt.png
/usr/share/images/,ACCESS,edge_lt.png
/usr/share/images/,"CLOSE_NOWRITE,CLOSE",edge_lt.png
```

The invocation from `rc.S` ensures that logging is done in a
comma-separated CSV format that is easy to import elsewhere, for example
into a spreadsheet or database. How to interpret the individual data can
be found in the Inotify-Tools documentation; it is not Freetz-specific.

If other data should be collected, for example accesses to the RAM disk
should also be logged, only a specific directory should be monitored, or
only write operations should be observed, `inotifywait` can still be
started manually, or `inotifywatch` can be used for prebuilt statistics.

### Consolidate the Log File Regularly to Save Space

For the purpose of saving space in firmware images, we are probably less
interested in which files were accessed in which order, how often, and in
which way (read, write, create, delete, etc.), but only in which files
were accessed *at all* or which were not, because those would then be
missing from the log. For this, cumulative output would be useful, which

-   condenses the log when it exceeds a certain size into a list of pure
  path and file names, sorted alphabetically by path,
-   merges this condensed list with any previous version and removes
  duplicates,
-   deletes the large log and briefly stops logging in between for this
  purpose,
-   restarts logging into the large log until the maximum size is reached
  again,

and so on, in a loop. I have the following script in my
`/var/tmp/flash/rc.custom`, so it is executed after the end of the Freetz
startup process:

```
# Create script for continuous file access logging and log file consolidation
cat << 'EOF' > /var/tmp/iw_continuous
#!/bin/sh

# If inotify logging is inactive, start it
if [ "$(/etc/init.d/rc.inotify_tools status)" != "running" ]; then
/etc/init.d/rc.inotify_tools start
fi

MAX_LOG_SIZE=$(( 10 * 1024 ))
while true; do
sleep 60
if [[ $(( $MAX_LOG_SIZE - $(cat /var/iw.log | wc -c) )) -gt 0 ]]; then
    #echo "current size of iw.log < $MAX_LOG_SIZE - continue logging"
    continue;
fi
#echo "current size of iw.log >= $MAX_LOG_SIZE - consolidate file list and restart logging"
cat /var/iw.log | grep '^/' | sed 's/,.*,//' | sort | uniq | sed 's//////' > /var/iw-unique.tmp
touch /var/iw-unique.log
cat /var/iw-unique.log >> /var/iw-unique.tmp
cat /var/iw-unique.tmp | sort | uniq > /var/iw-unique.log
rm -f /var/iw-unique.tmp /var/iw.log
/etc/init.d/rc.inotify_tools start
done
EOF

chmod +x /var/tmp/iw_continuous

# If inotifywait is already running, start continuous logging script
if [ "$(/etc/init.d/rc.inotify_tools status)" == "running" ]; then
/var/tmp/iw_continuous > /dev/null 2>&1 &
fi
```

The script creates another executable script that is started in the
background and performs the actual continuous consolidation of the large
log. The consolidated list of files is regularly updated in
`/var/iw-unique.log`, where it can be viewed at any time. It looks
roughly like this (excerpt):

```
/
/etc/.subversion
/etc/default.callmonitor/system.cfg
/etc/init.d/rc.bftpd
/etc/init.d/rc.cifsmount
/etc/init.d/rc.crond
/etc/init.d/rc.dropbear
/etc/init.d/rc.inotify_tools
/etc/init.d/rc.mini_fo
/etc/init.d/rc.nfsroot
/etc/init.d/rc.samba
/etc/init.d/rc.swap
/etc/init.d/rc.syslogd
/etc/init.d/rc.telnetd
/etc/init.d/rc.webcfg
/etc/init.d/rc.wol
/etc/static.pkg
/lib/libgcc_s.so.1
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avalanche_led/
/lib/modules/2.6.13.1-ohio/kernel/drivers/char/avm_event/
/lib/modules/2.6.13.1-ohio/modules/
/usr
/usr/
/usr/lib/callmonitor/applets/rc.callmonitor.sh
```

### Closing Word

This provides a powerful analysis tool, now finally documented after the
fact, that will hopefully expand the possibilities of the "space-saving
disciples" a little. Have fun trying it out. Patience, you will figure
it out; it took me a while too. Unfortunately, for obvious reasons I did
not have this documentation. ;-)

The origin of this package in the forum was my idea and request
[there](http://www.ip-phone-forum.de/showthread.php?t=134151). Current
discussion about the package and this article can take place in the new
topic [Package Inotify-Tools +
Applications](http://www.ip-phone-forum.de/showthread.php?t=150597)

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)
