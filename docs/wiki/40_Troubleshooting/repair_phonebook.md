# Repair a Broken Phone Book

### Symptom

No new entries can be added. When trying to add one, this error appears:

> ERROR: phone book entry is faulty

### Cause

The file `/var/flash/phonebook` has become corrupted, regardless of how
or why it happened.

### Solution

As the path already suggests, a file in flash is broken and therefore
"only" needs to be replaced by a healthy one. Anyone with a Freetz backup
is in luck. Without a backup, the only option is to empty the phone book
completely:

```
    touch /tmp/leeredatei
    cat /tmp/leeredatei > /var/flash/phonebook
    rm /tmp/leeredatei
```

Afterwards, restart the box. The safest way is to briefly disconnect it
from power. During a normal reboot, it might otherwise save the corrupted
version from RAM back to flash before shutting down.

If you have a Freetz backup from a time when the phone book was still
valid, unpack the phone book from that archive, copy it to a USB stick or
to the box's RAM, and use it instead of the empty file to overwrite the
phone book in flash:

```
    # On the PC
    tar czf freetz-backup.tar.gz flash/phonebook
    scp flash/phonebook root@fritz.box:/tmp/newphonebook
    rm flash/phonebook
    rmdir flash
    # On the box
    cat /tmp/newphonebook > /var/flash/phonebook
    rm /tmp/newphonebook
```

Then disconnect the power again as described above.

> *Source: [IPPF
> Thread](http://www.ip-phone-forum.de/showthread.php?t=176144)*


