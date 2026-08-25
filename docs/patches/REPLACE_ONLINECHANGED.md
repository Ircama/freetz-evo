# Replace onlinechanged - EXPERIMENTAL
Onlinechanged is triggered by a custom IP watchdog (also works on IP clients).<br>
<br>

This patch ensures that the onlinechanged scripts of

 * AVM services (directory /etc/onlinechanged),
 * Freetz packages (directory /etc/onlinechanged),
 * onlinechanged CGI (script /tmp/flash/onlinechanged-cgi) and
 * manually created scripts (directories /tmp/onlinechanged and /tmp/flash/onlinechanged)

are triggered by a custom IP watchdog instead of AVM's multid.
<br>
Advantages of this method over the AVM mechanism:

 * In contrast to the AVM method, it also works on devices that do not establish their own internet connection (e.g. via DSL or PPPoE), i.e. on devices behind a NAT (e.g. with "Share internet connection").
 * In problem cases where AVM onlinechanged does not work reliably (see the corresponding IPPF topic), this patch offers a reliable alternative.

More background on how it works can be found in the help text in "menuconfig".

### FAQ

 * AVM onlinechanged could also be called manually from the console via ```onlinechanged online```. How does this work with the IP watchdog, which is constantly running in the background?<br>
   Simply: ```killall ip_watchdog```. The command terminates the running instance, and ```init``` immediately restarts the watchdog (because of the "respawn" directive in /etc/inittab).
   This causes all onlinechanged scripts to be executed once. Afterwards it continues to run normally, i.e. the scripts are only called again
   when the external IP address changes. In contrast to ```onlinechanged online``` (only works without this patch anyway) or ```/bin/onlinechanged.sh online``` (works with this patch too),
   the killall method ensures that everything is initialized cleanly (e.g. ```IPADDR```, see also the next question).

 * How do I determine the external IP address in my own onlinechanged scripts?<br>
   The IP watchdog determines it anyway and passes it in the environment variable ```IPADDR```, which can be used in the corresponding scripts.
   This saves calls to get_ip and thus possibly also requests to external STUN servers.
   This also makes caching of the IP address unnecessary. The variable ```IPADDR``` is also set in the AVM original by multid when onlinechanged is called.
