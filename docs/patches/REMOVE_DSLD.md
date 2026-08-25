# Remove dsld
Removes the DSL daemon - the box can then only be used as an IP client.
Caution! Without dsld, the box cannot establish a DSL connection and "Internet over LAN" also no longer works, because dsld also takes over firewall and NAT.<br>
<br>

The DSLd is ```an AVM daemon that takes care of the DSL interface. On the FBF 7050 it also does the NAT for all packets going through its interface.``` (Fritzbox-Wiki).
If you don't use the box for DSL dial-up (but e.g. behind another FRITZ!Box that takes care of DSL etc.), you can free up a little space in the image by removing the DSLd.

 * Everyone else should better keep their hands off it ;)

### Further links

 * [Fritzbox-Wiki: DSLd](http://www.wehavemorefun.de/fritzbox/index.php/Dsld)
 * [Blog: Fritz!Box re-connect](http://blog.gauner.org/2008/03/19/fritzbox-reconnect/)
