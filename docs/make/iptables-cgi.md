# Iptables-CGI - DEPRECATED
  - Package: [master/make/pkgs/iptables-cgi/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/iptables-cgi/)
  - Steward: -

**iptables-CGI** is a web frontend for
[iptables](http://de.wikipedia.org/wiki/Iptables).
iptables can be used to implement firewall rules by creating or deleting
individual port rules. iptables is used, among other things, by
[knockd](knock.md).

### Installation

iptables-cgi can be selected in `make menuconfig` if iptables is marked.

### Frequently Asked Questions / Howto

The functions and history of iptables are not repeated or described here,
because there is already enough documentation about them on the internet.
A very good page, for example, is the following:
[http://de.wikipedia.org/wiki/Iptables](http://de.wikipedia.org/wiki/Iptables)

Only the iptables web interface is covered here, with simple explanations
of how to work with it.

### Activation

If "Active" is selected here, the iptables modules are loaded when the
box starts.

When "Stop" is used under Services, the rules and modules are unloaded.

### iptables add/remove rule

  --------------------- ----------------------------------------------------------------------
  **Label**             **Function**
  Add                   Adds a new rule
  Insert                Inserts a new rule at the position specified under "Position"
  Position (ID)         This field can only be used together with Insert
  Chain                 Specifies the table in which the rule should be stored
  Source Address        Defines the outgoing IP address (host)
  Destination Address   Defines the target IP address (host)
  Port                  Specifies the source/destination port (ANY = all)
  Protocol              The protocol used = tcp, udp, icmp (ping)
  Interface             Specifies the interface on which the rule should apply
  NAT                   Network Address Translation / address masquerading
  Action                Specifies whether to allow (Accept), deny (Drop), or log (LOG)
  --------------------- ----------------------------------------------------------------------

For the fields **Source Address** and **Destination Address**, host names
stored in HOSTS can also be entered. The box performs automatic name
resolution.

### Services

The services selectable under **Port** are stored under *Settings ->
Iptables: Services* and can be extended as desired. Please use the
following syntax:

```
Service:Port   z.B. SSH:22
```

### Rules

The rules are permanently stored in the box's flash memory and are
therefore not lost. This rule list can also be changed manually under
*Settings -> Iptables: Rules*. When this list is saved, the rules are
applied immediately.

### Deleting Rules

Rules can be deleted either via the *Remove* link to the right of the
corresponding rule, or manually under *Settings -> Iptables: Rules*.

### Important Notes

Various forums circulate the half-truth that IPTables is unstable and
causes the box to reboot without provocation. This is not entirely
correct: IPTables itself runs stably. The problems are caused by the
**conntrack** module if it is loaded. Since it is not strictly required
for the general function of IPTables, it does not have to be installed.

 * When selecting iptables-cgi in `make menuconfig`, *conntrack* may be
recursively selected. However, it can be deselected manually so that it is
not installed.

