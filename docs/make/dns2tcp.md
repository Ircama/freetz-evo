# dns2tcp 0.5.2 - DEPRECATED
  - Package: [master/make/pkgs/dns2tcp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/dns2tcp/)
  - Steward: -

**Dns2tcp** was developed to tunnel TCP connections over DNS traffic. The
data encapsulation already takes place at the TCP level, so no separate
driver (TUN/TAP) is required. The *Dns2tcp* client does not need to run
with special privileges.

*Dns2tcp* consists of two parts: a server-side tool and a client-side
tool. From its configuration file, the server knows a list of resources;
each resource is a local or remote service that listens for TCP
connections. The client listens on a predefined TCP port and forwards each
incoming connection over DNS to the target service.

### Using with FreeDNS

None of my hosting providers allowed me to set NS records, not even for
a subdomain, which seems to be common. I found out it is also possible
to use FreeDNS for this purpose.

Assuming you have a
([DynDNS](http://www.dyndns.com/)) domain name
pointing to your Fritz!Box, lets say *fabulous.fritzbox.org*, you can do
this:

1.  Register at
    [FreeDNS](http://freedns.afraid.org/)
2.  Create a FreeDNS subdomain:
    -   Type: *NS*
    -   Subdomain: anything you like, for example *dns2tcp*
    -   Domain: anything you like, for example *strangled.ne*t
    -   Destination: for example *fabulous.fritzbox.org*
3.  Set *dns2tcp.strangled.net* as DNS name using the *dns2tcp* WebIF
4.  On the client you should be able to create a DNS tunnel like this
    now:

    ``` 
    dns2tcpc -r ssh -l 2222 -z dns2tcp.strangled.net fabulous.fritzbox.org
    ```

5.  If you want a local
    [SOCKS](http://en.wikipedia.org/wiki/SOCKS)
    server to browse the internet:

    ``` 
    ssh root@localhost -p 2222 -D 8765
    ```

6.  If you want to use [Polipo?] as http proxy:

    ``` 
    ssh root@localhost -p 2222 -L 8123:localhost:8123
    ```

A few notes:

1.  Don't forget to forward port UDP 53 to *dns2tcpd*, for example
    using [AVM-Firewall](avm-firewall.md)
2.  *dns2tcp* works with [dnsmasq](dnsmasq.md), if you forward
    to a port other than 53
3.  Use [dropbear](dropbear.md) or *OpenSSH* as SSH server
4.  Security advice: disable SSH password login and use a certificate to
    login
5.  You can setup dynamic DNS using the regular Fritz!Box interface:
    -   Advanced settings | Internet | Permit Access | Dynamic DNS
6.  There is no Windows client available (you could try
    [iodine](iodine.md))

### Further Links

-   [Dns2Tcp
    Homepage](http://www.hsc.fr/ressources/outils/dns2tcp/)
-   [Article: TCP over DNS with
    dns2tcp](https://netzhure.de/2007/10/22/127-TCP-over-DNS-mit-dns2tcp.html)
-   [IPPF forum discussion about
    Dns2Tcp](http://www.ip-phone-forum.de/showthread.php?t=156586)

