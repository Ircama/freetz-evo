# Remove CAPIoverTCP
Removes the CAPIoverTCP interface of the FRITZ!Box.
Caution! CAPIoverTCP is used by several useful PC programs for accessing the box!
FritzFax, for example, uses this interface to send faxes from the PC via the FRITZ!Box.<br>
<br>

This patch removes the binary "capiotcpserver" (size 13 KB) from the firmware. This binary normally listens on port 5031.

### CAPIoverIP under Windows

Under Windows, CAPIoverIP is used, among others, by:

 * FritzFax
 * Outlook dialing assistant (for accessing the FRITZ!Box)
 * [DisplayCall](http://www.lachenmann-net.de/displaycall/)
 * [Phoner](http://www.phoner.de/)

### CAPIoverIP under Linux

CAPIoverTCP can also be used under Linux, as described in this [Howto](http://wiki.ip-phone-forum.de/gateways:avm:howtos:mods:remotecapi), for example to

 * send and receive faxes using a soft-DSP
 * make phone calls with a headset
 * connect to Asterisk

### CAPIoverIP on the Mac

If anyone here knows something, please add it!
Further links

 * [CAPIoverTCP in the Fritzbox Wiki](http://www.wehavemorefun.de/fritzbox/Nutzung_des_Capi-over-TCP_Server_der_Fritzbox)
 * [AVM FAQ on Fritz!Fax](http://www.avm.de/de/Service/FAQs/FAQ_Sammlung/11843.php3)
 * [a-sa Wiki: Faxing via the FRITZ!Box](http://a-sawicki.de/cms/index.php?option=com_content&task=view&id=38&Itemid=29)
 * [Howto: CAPIoverIP under Linux](http://wiki.ip-phone-forum.de/gateways:avm:howtos:mods:remotecapi)
