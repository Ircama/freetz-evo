# Separate WLAN from LAN with iptables

This guide explains how to restrict access from the FRITZ!Box WLAN, for
example to make WLAN available to everyone without putting the internal
LAN or the FRITZ!Box itself at risk.

### FRITZ!Box Setting

First, in the FRITZ!Box web interface under *System -> Network Settings
-> IP Addresses*, disable the option *"All computers are located in the
same IP network"*; see also the
[screenshot](/screenshots/48 "Settings for separate networks (Fritz!Box 7050)").
This not only separates the networks, it also creates a new interface
named *wlan*.

### iptables

Now the iptables rules can be set. These are simple commands executed on
the command line through *telnet* or *ssh*. If they should survive a
reboot, place them for example in `/var/flash/debug.cfg`.

### Secure the Network

```
    iptables -A FORWARD -i wlan -o dsl -j ACCEPT
    iptables -A FORWARD -i wlan -j DROP
```

This protects the internal network, but not the box itself.

```
    iptables -A INPUT -i wlan -p tcp -j DROP
    iptables -A INPUT -i wlan -p udp -j DROP
```

Now TCP/UDP access to the box is also blocked, though it still answers
pings.

### Allow Access

However, the DNS server is no longer reachable either, and computers in
the WLAN can no longer resolve domain names, for example *www.wikipedia.org*
instead of `145.97.39.155`.

iptables processes rules in order. The **-A** option in the commands
above means *append*, so the rules were inserted at the *end of the list*.

With **-I** for *insert*, rules can be placed at the *beginning of the
list* to create exceptions for specific services, for example DNS via TCP
and UDP.

```
    iptables -I INPUT -i wlan -p tcp --dport 53 -j ACCEPT
    iptables -I INPUT -i wlan -p udp --dport 53 -j ACCEPT
```

Afterwards, computers in the WLAN can use the internet connection as
usual without having access to the box's web interface or to computers in
the LAN.

Access to the box can be extended as needed using this pattern:

```
    iptables -I INPUT -i wlan -p <Protokoll> --dport <Port> -j ACCEPT
```

erweitern.

### Examples

```
    # ssh
    iptables -I INPUT -i wlan -p tcp --dport 22 -j ACCEPT
    # OpenVPN
    iptables -I INPUT -i wlan -p udp --dport 1194 -j ACCEPT
```


