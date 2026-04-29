# pptpd 1.4.0 - DEPRECATED
  - Homepage: [https://sourceforge.net/projects/poptop/](https://sourceforge.net/projects/poptop/)
  - Changelog: [https://sourceforge.net/projects/poptop/files/pptpd/](https://sourceforge.net/projects/poptop/files/pptpd/)
  - Repository: [https://sourceforge.net/p/poptop/git/ci/master/tree/](https://sourceforge.net/p/poptop/git/ci/master/tree/)
  - Package: [master/make/pkgs/pptpd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/pptpd/)
  - Steward: -

The interface itself is easy to understand ;-).

The links to the individual configuration files can be found under
**Settings**.

An overview of the available settings is provided by the Poptop
documentation on their
[Homepage](http://poptop.sourceforge.net/dox/).

-   **"Edit pptpd settings"** edits the file
    [pptpd.conf](http://poptop.sourceforge.net/dox/pptpd.conf.txt)
	-   path specifications for the binary and the configuration file
	-   enable possible debug information
	-   define the server IP (default: localip 192.168.178.1)
	-   define the IP range of logged-in computers (default: remoteip
        192.168.178.210-229 )
	-   miscellaneous
-   **"Edit PPPD settings"** edits the file
    [options.pptpd](http://poptop.sourceforge.net/dox/options.pptpd.txt)
	-   name of the PPTP server (default: fritzbox)
	-   specify which protocols are allowed
	-   define DNS servers for clients (default: ms-dns
        192.168.178.1)
	-   miscellaneous
-   **"Edit password"** edits the file
    [chap-secrets](http://poptop.sourceforge.net/dox/chap-secrets.txt)
	-   manages authorized users and their passwords

[![pptpd settings](../screenshots/38_md.png)](../screenshots/38.png)

### Port Forwarding

To ultimately be able to connect to the PPTP server from the outside,
port forwarding to the IP of the FRITZBox must of course be configured.

```
	Protocol: TCP  Port: 1723
	Protocol: GRE  (no port specification needed)
```

See also the following packages:

-   [Virtual IP](virtualip-cgi.md)
-   [AVM Firewall CGI](avm-firewall.md)

### Configuration

The three files relevant for Poptop can be edited either through the web
interface or on the shell using vi. They are located in the directory
`/tmp/flash/ppp`.

### pptpd.conf

In the supplied configuration, logwtmp is enabled by default (refers to
version 1.1.2-stable; already fixed in 'trunk'). This should be disabled,
because wtmp does not run on the fritzbox and therefore no VPN connection
is established.

```
	# TAG: logwtmp
	#       Use wtmp(5) to record client connections and disconnections.
	#
	#logwtmp
```

If the data rate from WLAN to the internet is very slow with pptpd, the
line `bcrelay` should be commented out (see
[IPPF](http://www.ip-phone-forum.de/showthread.php?t=201539))

### options.pptpd

The file options.pptpd may contain `require-mppe-128` (refers to version
1.1.2-stable; already fixed in 'trunk'). However, pppd does not know this
option. When negotiating encryption with the client's 'Auto' setting,
connection problems may occur if the client first wants to negotiate, but
pppd wants to speak encrypted immediately. Encryption can be fixed
directly to 128 bit. With this setting, a PPTP connection with the iPhone
VPN client worked:

```
	# Require the peer to authenticate itself using MS-CHAPv2 [Microsoft
	# Challenge Handshake Authentication Protocol, Version 2] authentication.
	require-mschap-v2
	# Require MPPE 128-bit encryption
	# (note that MPPE requires the use of MSCHAP-V2 during authentication)
	#require-mppe-128

	mppe required,no40,no56,stateless
```

### chap-secrets

In `options.pptpd`, the name is set to `fritzbox`. This should then be
reflected in a user entry in `chap-secrets`:

```
	# client        server  secret                  IP addresses
	username fritzbox password 192.168.x.y
	EOF
```

In many examples on the internet, the second column contains `pptpd`. If
that is desired, simply adjust the `name` entry in `options.pptpd`
accordingly.

### Troubleshooting

To see the pptpd messages, first start a syslogd:

```
	/var/tmp/flash/ppp # syslogd -L -C256 -l 7
```

After that, the daemon's syslog messages can be viewed with `logread`:

```
	/var/tmp/flash/ppp # logread
```

To get more messages, debug mode can be enabled in `options.pptpd` and/or
`pptpd.conf`:

options.pptpd:

```
	# Enable connection debugging facilities.
	# (see your syslog configuration for where pppd sends to)
	debug
```

pptpd.conf:

```
	# TAG: debug
	#       Turns on (more) debugging to syslog
	#
	debug
```

### Troubleshooting No Error Message

In my case, no error message appeared in the log. Debugging on the box
with the following helps:

```
	./strace pptpd -d -f -c /etc/ppp/pptpd.conf
```

This showed that the following error message exists:

```
	can't resolve symbol 'bzero'
```

There is a thread about this in the forum; the last post explains how the
toolchain must be rebuilt to fix it:
[http://www.ip-phone-forum.de/showpost.php?p=1407147&postcount=25](http://www.ip-phone-forum.de/showpost.php?p=1407147&postcount=25)

Update [2011-07-18]: The problem should no longer occur with Freetz 1.2
or a current trunk.

