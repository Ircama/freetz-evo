# pptp 1.10.0
  - Homepage: [https://sourceforge.net/projects/pptpclient/](https://sourceforge.net/projects/pptpclient/)
  - Changelog: [https://sourceforge.net/projects/pptpclient/files/pptp/](https://sourceforge.net/projects/pptpclient/files/pptp/)
  - Repository: [https://sourceforge.net/p/pptpclient/git/ci/master/tree/](https://sourceforge.net/p/pptpclient/git/ci/master/tree/)
  - Package: [master/make/pkgs/pptp/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/pptp/)
  - Steward: [@fda77](https://github.com/fda77)

`"PPTP Client is a Linux, FreeBSD, NetBSD and OpenBSD client for the proprietary Microsoft Point-to-Point Tunneling Protocol, PPTP. Allows connection to a PPTP based Virtual Private Network (VPN)."`

Many companies use Microsoft's PPTP server. With this client, a
connection to such a VPN can be established via the **Point-to-Point
Tunneling Protocol** (**PPTP**).

 * The PPTP package requires "replace kernel".

### PPTP Configuration

**Hostname**: `VPN server` (example: vpn.tolledomain.de)
**Username**: `VPN username` (with Windows, write the domain like this:
DOMAIN/user or DOMAINuser, not DOMAINuser)
**Servername**: `PPTP`

### IP Routing

Enable it and write the company network, including subnet mask, into the
text field (for example 10.0.0.0 255.255.255.0).

Apply the changes and open the page again. Now click
`PPPD: edit chap-secrets` and enter the following there:
`VPN-Username PPTP VPN-Password *`
*Important*: replace VPN-Username and VPN-Password with your own values.

After that, start the PPTP package under Services and, via SSH from the
Fritzbox, ping a computer in the company network.

Routing/NAT information to follow.

Screenshot?

