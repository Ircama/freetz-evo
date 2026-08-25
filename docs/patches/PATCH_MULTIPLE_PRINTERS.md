# Add support for multiple printers
Enables the use of multiple printers on the FRITZ!Box.<br>
<br>

This patch is based on the idea from [this post](http://www.ip-phone-forum.de/showthread.php?t=161756&p=1075666) of coupling connected printers and their respective print server ports via the physical USB port. This ensures a fixed assignment.

Since the AVM print server occupies two ports each (n+1), one port is always skipped:

```
phys. USB port 0 => Port 9100
phys. USB port 1 => Port 9102
phys. USB port 2 => Port 9104
...
```

All printers should be connected to the same USB hub. In principle, different hubs are also possible with restrictions.
The "USB devices" overview lists all connected printers with their assigned print server ports.
The printer on physical USB port 0 (port 9100) is also always registered as the default printer (device node /dev/usblp0) - if connected. This makes sense at the latest when the FRITZ!Box should provide its own printing functions (such as direct fax printing).

### Restrictions

The displayed printer status arbitrarily switches between the connected printers.

-by IPPF user thimo

### Further links

    http://www.ip-phone-forum.de/showthread.php?t=161756
    http://www.ip-phone-forum.de/showthread.php?t=195811
