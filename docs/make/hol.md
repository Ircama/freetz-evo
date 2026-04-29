# Halt-On-Lan 1.0 - DEPRECATED
  - Package: [master/make/pkgs/hol/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hol/)
  - Steward: -

Halt-on-Lan is a package for controlling computers in the local network
from the FritzBox. It is based on
[poweroff.exe](http://users.telenet.be/jbosman/poweroff/poweroff.htm)
which is a script for Windows computers. It speaks the same language and
allows the computer to be shut down, restarted, and a few other actions.
Since
Changeset r5024
the HOL package has been in trunk.
In the long term, HOL is intended to be combined with WOL and HOL actions
are to be made available from the extended WOL WebIF. This is not
implemented yet, so for now you should get comfortable with the command
line:

```
/var/mod/root # hol
hol v1.0 Halt-On-Lan script
Author hermann72pb <http://www.ip-phone-forum.de/member.php?u=80424>

Usage: hol HOST [ACTION TIME MESSAGE]
HOST      Hostname or ip address: e.g. my.computer or 192.168.178.20
ACTION    Actions for poweroff: e.g. shutdown, reboot, logoff, lock, etc.
TIME      time in seconds for warning before the action:
          e.g. 10 or 0 for no warning
MESSAGE   Warning message: e.g. Please close all your files
/var/mod/root # hol 192.168.178.20
/var/mod/root # hol 192.168.178.20 lock
/var/mod/root # hol MeinPC monitor_off 15
/var/mod/root # hol DeinNotebook monitor_off 15 "Hey, dunschalte aus!"
```

HOL calls can already be used as callmonitor actions or as cron entries.
There is a configuration page for the HOL package in the FREETZ WebIF for
configuring default actions and other parameters. However, actions cannot
be initiated from this configuration page.

Further information and discussion about the HOL package can be found in
the corresponding
[Thread](http://www.ip-phone-forum.de/showthread.php?t=211366)
thread in IPPF.
To control the computer from the FritzBox, a poweroff.exe-compatible
application must be running on the computer. This can be, for example,
[poweroff.exe](http://users.telenet.be/jbosman/poweroff/poweroff.htm)
itself. Since
[poweroff.exe](http://users.telenet.be/jbosman/poweroff/poweroff.htm)
unfortunately does not seem to work correctly and reliably,
the user
[linuxkasten](http://www.ip-phone-forum.de/member.php?u=217599)
from IPPF wrote an alternative
([remotehalt](http://www.nefkom.info/crats/software/remotehalt/))
for Windows. It is recommended from now on to use
[remotehalt](http://www.nefkom.info/crats/software/remotehalt/)
instead of
[poweroff.exe](http://users.telenet.be/jbosman/poweroff/poweroff.htm)
.
Suitable solutions for Linux users are also currently being worked on. On
the one hand, there is a tarred
[Sammlung](http://www.ip-phone-forum.de/showpost.php?p=1501078&postcount=1)
collection for unpacking and installing manually; on the other hand,
there is also an
[inetd-Variante](http://www.ip-phone-forum.de/showpost.php?p=1553804&postcount=39).
inetd variant. As soon as all computer-side applications are fully
implemented and sufficiently tested, the [download](../Download.html)
information here will be revised.

