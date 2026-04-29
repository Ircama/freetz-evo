# owfs 2.7p32 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/owfs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/owfs/)
  - Steward: -

This package provides functions similar to the digitemp package, with the
advantage that a larger selection of chips is supported. Integration into
the Freetz interface is not available yet.

For longer distances (x00m), the 1-Wire bus should be built at least
with shielded/twisted-pair cables. As with any bus, branches must not be
too long, i.e. less than 1 m, so reflections do not interfere with the
data signal. The DS9490R USB 1.1 adapter has currently been tested as a
bus master on a Fritzbox.

The package is built without FUSE support, but the shell tools provide
equivalent functionality. In general, an owserver must be started; it
serializes and manages requests to the bus. Connections use port 4304 by
default.
` owserver --usb=ALL `

owhttpd is a mini web server and allows convenient bus debugging through
a web browser
([http://fritz.box:99](http://fritz.box:99))
` owhttpd -s 127.0.0.1:4304 -p 99 `
Of course, it does not necessarily have to run on the Fritzbox, because
the `-s` option defines the TCP/IP connection parameters to any
`owserver`.

owdir, owread, and owwrite allow easy reading and writing of 1-Wire
devices in the shell or in shell scripts.

More information is available in the man pages under "Further Links".

### Further Links

-   [http://owfs.org/](http://owfs.org/)
-   [A Guide to the 1WRJ45
    Standard](http://1wire.org/index.html?target=p_2.html&lang=en-us)


