# Enable custom UDEV rules
Custom rules evaluated by UDEV can be stored.<br>
<br>

With this patch, 2 additional freely usable rules are created and linked to /tmp/flash/mod/. They can be edited via the web interface in a submenu of "Freetz".

 * first (00-custom.rules): is executed before all AVM rules
 * final (99-custom.rules): is executed after all AVM rules

This allows USB devices to be assigned fixed names:

```
SUBSYSTEMS=="usb", KERNEL=="ttyUSB*", ATTRS{serial}=="7CF6976", SYMLINK+="reader1"
SUBSYSTEMS=="usb", KERNEL=="ttyUSB*", ATTRS{serial}=="FDF4F0D", SYMLINK+="reader2"
SUBSYSTEMS=="usb", KERNEL=="ttyUSB*", ATTRS{serial}=="40ABBFF", SYMLINK+="lcd1"
```
