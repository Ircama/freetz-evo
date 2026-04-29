# Onlinechanged-CGI
  - Package: [master/make/pkgs/onlinechanged-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/onlinechanged-cgi/)
  - Steward: -
<br>

AVM firmware contains a mechanism which ensures that

 * when the box starts (parameter $1 has the value "start"),
 * when the internet connection is disconnected (parameter $1 has the value "offline"), and also
 * when the internet connection is re-established (parameter $1 has the value "online"),

the script /bin/onlinechanged is called. It in turn calls additional scripts below the directories /etc/onlinechanged and
/var/tmp/onlinechanged, if present. These scripts (re-)initialize various services, such as WebDAV (online storage).

Various Freetz packages also need the ability to perform certain actions when the connection status changes, for example registering DynDNS hostnames
with a new IP address, rebuilding VPN connections, and so on. The Onlinechanged-CGI package additionally allows the user to trigger custom actions,
for example sending an email with the current IP address to the user.

 * Note: AVM Onlinechanged works only on devices configured to establish the internet connection themselves, usually via DSL or PPPoE. It does not
    work on boxes behind NAT, for example with "share existing internet connection". If Onlinechanged should also run on such devices, this is possible
    with the "replace onlinechanged" patch, which is also used in problem cases on devices where AVM Onlinechanged does not work reliably (see the
    corresponding IPPF topic).


This feature has been in Freetz since r2850 (trunk) and was implemented because AVM changed the behavior of /bin/onlinechanged in firmware 54.04.67.
Previously, /bin/onlinechanged was a symlink to the script /var/tmp/onlinechanged. Its creation can be traced in Ticket #271.

To unify the behavior, since r2850 the following applies to /bin/onlinechanged:
When the online status changes, the script is called by multid with online or offline as the parameter and then calls the following scripts itself:

 * /var/tmp/onlinechanged 	compatibility with the old behavior
 * /etc/onlinechanged/* 	new AVM behavior
 * /tmp/flash/onlinechanged/* 	scripts in Freetz flash

A script in /etc/onlinechanged could look like this, for example:
```
#!/bin/sh

case "$1" in
   online)
      /etc/init.d/rc.package online
      ;;

   offline)
      /etc/init.d/rc.package offline
      ;;
esac
```

An application: update external IP-address for dnsd:
```
EXTIP="`/usr/bin/get_ip -d`"
sed "s/#EXTIP#/$EXTIP/g"</tmp/flash/dnsd/dnsd_template.conf >/tmp/flash/dnsd/dnsd.conf
modsave
/etc/init.d/rc.dnsd restart
logger -t dnsd "IP set to $EXTIP"
```

You can send yourself an e-mail when your box comes online like this:

```
   online)
      mailer -s "Freetz online" -t <your e-mail address>
      ;;
```

For this to work, you should configure the ​AVM Push service, but it is not necessary to enable it. 

