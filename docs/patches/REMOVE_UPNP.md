# Remove UPnP (igdd/upnpd)
Removes the UPnP daemon. Caution! Without the UPnP daemon, FritzFax cannot be set up.<br>
<br>

uPnP stands for "universal Plug'n'Play". If enabled and released, clients can open ports on the box on demand.
On the one hand this is certainly quite practical, because you no longer have to do this manually in the web interface - but it also carries risks:
A trojan could also use this way to open its "highway home" - see also the article Hacking routers via uPnP.
With uPnP enabled on the box, you essentially give up a good deal of control.

Some AVM software needs this functionality (including FritzFax) - other programs possibly too. If you don't need it, you can remove it here.
And if you're not entirely sure, you can first disable it in the web interface and see if any program
complains - if that doesn't happen until the next firmware update, you can throw the stuff out then ;)

### What is removed?

With this patch, the uPnP daemon (igdd) is removed from the image. In addition, the init scripts are adjusted so that they don't stumble over its absence.

### What needs to be considered?

On the one hand, as already mentioned above: some software depends on the uPnP server here - it will most likely only work to a limited extent, if at all.

Furthermore, before flashing an image with the uPnP server removed, you should ensure that all uPnP features in the current image have been disabled.
The corresponding options can be found under "Settings => System => Network settings => Transmit status information via UPnP (recommended)".

### Further links

 * [Wikipedia: uPnP](http://de.wikipedia.org/wiki/Universal_Plug_and_Play)
 * [DSL re-connect via uPnP](http://blog.jbbr.net/2008/01/03/fritzbox-schneller-reconnect-unter-linux/)
 * [Hacking routers via uPnP](http://forum.ubuntuusers.de/topic/router-hacken-mit-hilfe-von-upnp/)
