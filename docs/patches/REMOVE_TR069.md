# Remove tr069
Removes tr069 (remote configuration by the provider). Without tr069, setup with the 1&1 start code is not possible.<br>
<br>

"TR69 is [...] a protocol that regulates the communication between a device and a control server." That's how a blog post (see below) describes it.
The FRITZ!Box uses it on the one hand to automate complex settings during box setup, and on the other hand so that the respective provider can access the customer's box configuration in support cases. This ranges from changing individual settings to firmware upgrades or detecting modifications.

For the disadvantages of activated TR-069, see in particular the second page of the second article in the link list below:
Obviously, TR-069 is already activated on FRITZ!Boxes from the factory, so that "Big Brother" already finds its snooping access ready for use.
If you take a look at the help script /bin/supportdata, you don't need to wonder why modifications are immediately detected by the provider in support cases, as are third-party services (e.g. VoIP).

Many of the dangers described in the FAQ when replacing the SSL libraries are also directly related to the TR069 service, which apparently needs the "original" AVM SSL libraries for the HTTPS-secured connection to the ACS server. With earlier firmware versions, disabling TR069 was sufficient here, but with newer firmwares the problems also appear then - perhaps an indication that the service can no longer be fully disabled at all.

 * Conflicts between Freetz modifications and TR069 usually only appear when DSL is connected, which makes the problem easy to narrow down. If a box runs stably until DSL is connected or synchronized, then this patch helps. Note the warning below!.

So in many respects it may be advisable to make use of the option of completely removing TR-069 here.
If you don't permanently need the support via TR-069 (or don't want it at all), you can spare the "tr069 stuff" in the image - and use the freed space for other things.

Warning: If TR069 is removed, neither automatic setup nor the start code will work.
Some providers have complicated multi-PVC settings for internet telephony that often cannot be entered via the web interface in that form.
Manual entry often works too, but is easy for the provider to detect and is often declared as unsupported in the terms and conditions (e.g. 1&1).

Also, in the event of an error, the support may withdraw any willingness to cooperate if the device was not or cannot be configured with TR069 - up to an alleged loss of warranty of the delivered device. In the branded web interface of such providers, TR069 also cannot be disabled.
Therefore the following procedure is recommended:

 * Perform a factory reset before modifying the firmware (except for new devices).
 * If the device has already been modified, save the Freetz settings and perform a recovery (set the original branding beforehand!).
 * Remove any USB storage if present.
 * Perform the setup procedure recommended by the provider (e.g. start code with 1&1).
 * After successful setup and working telephony, disconnect from DSL.
 * Flash the Freetz firmware with removed TR069 functionality - if applicable, restore ONLY the Freetz settings.
 * Reconnect DSL - peace at last.
 * In a service case, repeat the procedure (from recovery).

Tip: Before modifying your box, you should make a copy of the environment so that you can compare it later.
The environment remains unchanged during a recovery and may contain traces of modifications.
There are several methods to do this:

 * FTP to ADAM2 and PRINTENV there
 * Via telnet/ssh into the box (leaves traces => factory reset afterwards) and cat /proc/sys/urlader/environment

### Further links

 * [Info on TR-069](http://www.jodler.ch/bstocker/?p=335)
 * [TR-069: Router plug-and-play with risks](http://www.netzwelt.de/news/78076-tr-069-router-plug-and-play-mit-risiken.html)
 * [Heise: TR-069 in operation](http://www.heise.de/netze/DSL-fernkonfiguriert--/artikel/99963/3)
 * [IPPF thread: understanding and using tr069](http://www.ip-phone-forum.de/showthread.php?t=146089)
