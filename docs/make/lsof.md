# lsof 4.89 (binary only) - DEPRECATED
  - Homepage: [https://people.freebsd.org/~abe/](https://people.freebsd.org/~abe/)
  - Manpage: [https://lsof.readthedocs.io/](https://lsof.readthedocs.io/)
  - Changelog: [https://github.com/lsof-org/lsof/releases](https://github.com/lsof-org/lsof/releases)
  - Repository: [https://github.com/lsof-org/lsof](https://github.com/lsof-org/lsof)
  - Package: [master/make/pkgs/lsof/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/lsof/)
  - Steward: -

`lsof` can determine which files are currently open, where, and by whom.
This can be very helpful when, for example, you want to remove an
attached removable medium (USB stick or USB hard disk) from the box, but
the filesystem cannot be unmounted because it is still in use. `mount`
only says that this is the case; it does not provide any details.

Example:

```
# lsof /var
COMMAND     PID     USER   FD   TYPE DEVICE SIZE/OFF     NODE NAME
syslogd     350     root    5w  VREG  222,5        0 440818 /var/adm/messages
syslogd     350     root    6w  VREG  222,5   339098   6248 /var/log/syslog
cron        353     root  cwd   VDIR  222,5      512 254550 /var -- atjobs
```

More information is available, among other places, at
[Wikipedia](http://en.wikipedia.org/wiki/Lsof).

