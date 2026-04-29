# Sundtek DVB driver 130210.134617/170310.204343/210803.071224 - DEPRECATED
  - Package: [master/make/pkgs/sundtek/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/sundtek/)
  - Steward: -

[![Sundtek DVB driver](../screenshots/256_md.jpg)](../screenshots/256.jpg)

This package provides the driver for Sundtek USB sticks that can receive
DVB (c/s/t).

 * The Fritzbox should have at least USB 2.0; 11 MBit/s is not enough.
 * With kernel 2.6.19.2 (Fritzbox 7270v1 and 7570), there is currently a
memory leak; see
Ticket #472

### Parameters for 'mediaclient'

Parameters for initializing `mediaclient` can be entered in this text
field. If this is used, hardware detection by `mediasrv` is awaited,
which takes about 10 seconds.

### Using the Driver

To use the driver, this command must be run first:

```
export LD_PRELOAD=/usr/lib/libmediaclient.so
```

### Initializing the USB Stick

For the Fritzbox, the USB stick must be switched to the "bulk" transfer
mode:

```
mediaclient --dtvtransfermode=bulk
```

This is needed only once, and the stick must then be plugged in again.

### Miscellaneous

It can be used, for example, to record the load of the cable internet
segment with [RRDstats](rrdstats.html#segment). Streaming to a Windows PC
with a current beta version of DVB-Viewer via SAT>IP is also said to be
possible.
