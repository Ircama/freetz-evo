# USB/IP 0.1.8 - DEPRECATED
  - Package: [master/make/pkgs/usbip/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/usbip/)
  - Steward: -

The goal of
**[USB/IP](http://usbip.sourceforge.net/)** is to make USB devices
attached to one computer usable from other computers, with their full
functionality. To do this, "USB I/O messages" are packed into IP packets
for transmission over the network. Each individual computer can then use
the corresponding USB devices as if they were directly attached to it.
This makes the following things possible:

-   **USB Storage Devices**: `fdisk`, `mkfs`, `mount`/`umount`, diverse
    file operations, playing movies from a DVD, burning a DVD...
-   **USB keyboards and USB mice**: use them both from the console and
    from the X Window System.
-   **USB webcams and USB speakers**: look through the webcam, capture
    image data, play music.
-   **USB printers**: like AVM printer sharing; additionally, for example,
    the ink level can be determined.
-   **USB scanners, USB serial converters, and USB network interfaces**:
    well, simply use them.

Implemented in hardware, there are already many so-called "USB extenders"
to be found through Google, and they make up by far the largest group of
search results. With this package, however, we teach the same trick to
existing hardware: our Freetz box.

IPPF describes how to use it: [part
1](http://www.ip-phone-forum.de/showpost.php?p=1392146&postcount=45)
[part
2](http://www.ip-phone-forum.de/showpost.php?p=1609255&postcount=50)

### Libraries Used

-   libglib2
-   libsysfs

### Further Links

-   [USB/IP
    project page](http://usbip.sourceforge.net/)
-   [IPPF thread: how USB/IP came to the
    Freetz-Box](http://www.ip-phone-forum.de/showthread.php?t=131278)
-   Windows-Client:
    [usbip_windows_v0.1.0.0_signed.zip](https://sourceforge.net/projects/usbip/files/usbip_windows/)


