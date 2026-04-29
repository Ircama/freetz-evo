# Configuration of the Built-in Switch

For supported models, see below.

For 7390 read this
[post](http://www.ip-phone-forum.de/showthread.php?t=287518&p=2185822&viewfull=1#post2185822).
For 7490 it should be possible by altering ar7.cfg. See the following
threads:
[1](http://www.ip-phone-forum.de/showthread.php?t=273927),
[2](http://www.ip-phone-forum.de/showthread.php?t=272055)
and
[3](http://www.ip-phone-forum.de/showthread.php?t=275391),
and possible others.

### Foreword

Some models from the FRITZ!Box family have not just one LAN port, but
four, for example the 7170. Since I personally know only the 7170, please
understand the following primarily as instructions and a description for
that model; please add information for other boxes.

In normal operation of the 7170, the four ports work like a normal
[Switch](http://de.wikipedia.org/wiki/Switch_(Computertechnik)),
meaning all connected devices are in the same subnet and can communicate
directly with each other. With AVM's original firmware, it is also
possible to use the LAN 1 port as a WAN port, by selecting *"internet
access via LAN 1"* in the web interface, for example when operating the
box behind a cable modem or similar. For this, the port is separated from
the remaining three ports and configured by the firmware as a separate WAN
network device.

This is possible because the FRITZ!Box contains a configurable 5-port
switch: four ports are exposed as LAN 1 to 4, and the fifth is connected
to the actual FRITZ!Box, meaning the CPU. Unfortunately, AVM's web
interface offers no way to configure the ports individually beyond that.
Because this would be very helpful in certain cases, the small tool
[cpmaccfg](http://www.heimpold.de/dsmod/) was created. It can be run on
the FRITZ!Box via Telnet/SSH access, or integrated directly into the
firmware image with Freetz.

AVM integrated the interface for switch configuration into the Linux
network-card driver, *avm_cpmac*. Apparently there is an "old" and a
"new" version of this interface. The old one still allows very extensive
access to the switch and makes it possible to exploit the full potential
of the switch. The new one is somewhat more abstract, which means only
different predefined configurations can be selected. Anyone needing full
access can reactivate the old interface by adding two lines of kernel
source code. In Freetz this happens automatically when `cpmaccfg` is
included, if `replace kernel` is selected in `menuconfig`.

The `cpmaccfg` tool also works on the Speedport W900V.

### Predefined Switch Configurations

AVM itself already stored several predefined configurations in the kernel
module. One of them is the previously mentioned variant "internet access
via LAN 1", internally called ATA mode. Here is an overview of all
predefined modes:

-   **normal**: all four ports work like a normal switch. The kernel uses
  `eth0` as the network interface. Depending on whether "All computers
  are in the same subnet" is checked, `eth0` is also bridged together
  with the WLAN interfaces into a `lan` interface.
-   **ata**: LAN 1 appears in the kernel as `wan`, the other three ports
  as `eth0`; possible integration of `eth0` into a bridge as in normal
  mode.
-   **split**: each port is assigned a separate interface, such as `eth0`,
  `eth1`, and so on.
-   **split_ata**: like split, but LAN 1 is named `wan`.
-   **all_ports**: basically like normal; exact purpose still unknown,
  possibly intended for boxes with more than four ports.
-   **special**: see below.

Changing the mode really makes sense only if the check mark for *"All
computers are in the same subnet"* is [not]{.underline} set, because
otherwise all available devices are put into a bridge. **UPDATE:** It also
works cleanly in `ethmode=ethmode_bridge`, because then the devices are
taken from the `Bridge` section and **not** from the `eth` section. In
`Eth-Bridge` mode, these individual real `ethX` devices are then
integrated into the specified bridge. This is quite practical if the USB
device, `usbrndis`, should be assigned to one of the four ports. The trick
is that the configured `ethx` interface in the `eth` section is also
listed in the bridge section.

Example: configure LAN1 and LAN4 as `eth2`, and LAN2 and LAN3 as `eth0`.
Then the `eth` section contains `eth0` and `eth2`, and the bridge section
contains, for example, bridge `lan` with interface `eth0` and bridge
`xnet` with interface `eth2`. If both are correctly present in `ar7.cfg`,
it is easy to switch between `ethmode=ethmode_bridge` and
`ethmode=ethmode_router`, AVM wording: "all computers are in the same
network", by setting or clearing the check mark. In
`ethmode=ethmode_bridge`, for example, interfaces `eth2` and `usbrndis`
can now be assigned to bridge `xnet`. Exactly how `ar7.cfg` is configured
is explained further below in this article.

The current mode can be queried with `cpmaccfg gsm`; it can be set with
`cpmaccfg ssm <target-mode>`.

### Mode `special`

With a patched kernel, it is also possible to create custom individual
port configurations. The `special` mode is used for this; it exists in
the kernel as a placeholder for a configuration. This placeholder must
first be filled with `cpmaccfg ssms ...`; afterwards,
`cpmaccfg ssm special` can switch to this configuration.

### Patch the Default Mode

Using special mode has the disadvantage that the mode must be activated
only during the box startup process. If the mode used by default in the
box, such as `NORMAL` or `ATA`, is changed, the switch is automatically
split appropriately when the box starts.

For this change, the desired mode must be patched in
`linux-2.6.19.2/drivers/net/avm_cpmac/cpphy_adm6996.c`. The following
example describes splitting the switch into the two interfaces `eth0`
with LAN1 and LAN2, and `eth1` with LAN3 and LAN4. The following patch
was created for a 7270 with firmware 76.

```
  --- linux-2.6.19.2/drivers/net/avm_cpmac/cpphy_adm6996.c_orig   2009-06-08 13:59:52.000000000 +0200
  +++ linux-2.6.19.2/drivers/net/avm_cpmac/cpphy_adm6996.c        2009-08-20 10:57:14.000000000 +0200
  @@ -137,9 +137,10 @@
                                           { {"", 0x0}
                                           }
                                      },
  -        /* CPMAC_MODE_NORMAL    */ { 1, 0xff,
  -                                        { {"eth0", 0x2f}
  -                                        }
  +        /* CPMAC_MODE_NORMAL    */ { 2, 0xff,
  +                                        { {"eth0", 0x23},
  +                                                 {"eth1", 0x2c}
  +                                       }
                                      },
           /* CPMAC_MODE_ATA       */ { 2, 0,
                                           { {"wan",  0x21},
```

Copy the patch into `/make/linux/patches/2.6.19.2` or, if applicable,
into a subdirectory such as `7270_04.76`.

```
  make menuconfig
```

Configure the box and select the option "Replace Kernel".

Delete the existing kernel:

```
  make kernel-dirclean
```

Prepare and patch the kernel sources:

```
  make kernel-source
```

Here you can check whether the patch is applied correctly, for example:

```
  applying patch file make/linux/patches/2.6.19.2/7270_04.76/990-cpmac.patch
  patching file linux-2.6.19.2/drivers/net/avm_cpmac/cpphy_adm6996.c
```

Then create the image:

```
  make
```

### Adjustments in ar7.cfg

Adjusting `ar7.cfg` ensures that the changes survive various
configuration changes, such as switching WLAN off and on, and that they
are automatically configured and remain configured.

Create a copy of `ar7.cfg` and edit it:

```
  cd /var/tmp
  cat /var/flash/ar7.cfg > ar7.cfg
  vi ar7.cfg
```

The box must be in `Router` mode; this is set with the `ethmode` option
in `ar7.cfg`.

```
  ethmode = ethmode_router;
```

Then the `ethinterfaces` section must be changed.

When configuring, note the following: only interfaces listed there receive
an IP address. All other interfaces do exist and can be queried with
`ifconfig` or configured manually if necessary.

For devices, bridges can be formed automatically using the `interfaces`
option. The following example describes the configuration of two devices,
`intern` and `extern`.

The device `extern` is formed from interface `eth1` with address
192.168.1.1. The device `intern` is formed from `eth0` and the various
WLAN interfaces with address 192.168.0.1. **UPDATE:** As you can see,
bridging already works cleanly in the `eth` section as well, and AVM did
the same with the WLAN interface.

```
        ethinterfaces {
                name = "extern";
                dhcp = no;
                ipaddr = 192.168.1.1;
                netmask = 255.255.255.0;
                dstipaddr = 0.0.0.0;
                interfaces = "eth1";
                dhcpenabled = no;
                dhcpstart = 0.0.0.0;
                dhcpend = 0.0.0.0;
        } {
                name = "eth0:0";
                dhcp = no;
                ipaddr = 169.254.1.1;
                netmask = 255.255.0.0;
                dstipaddr = 0.0.0.0;
                dhcpenabled = yes;
                dhcpstart = 0.0.0.0;
                dhcpend = 0.0.0.0;
        } {
                name = "intern";
                dhcp = no;
                ipaddr = 192.168.0.1;
                netmask = 255.255.255.0;
                dstipaddr = 0.0.0.0;
                interfaces = "eth0", "ath0", "wdsup1", "wdsdw1", "wdsdw2",
                             "wdsdw3", "wdsdw4";
                dhcpenabled = no;
                dhcpstart = 192.168.0.20;
                dhcpend = 192.168.0.200;
        }
```

Then overwrite the existing `ar7.cfg` with the modified file:

```
    cat /var/tmp/ar7.cfg > /var/flash/ar7.cfg
```

Then activate the changes with a reboot or `ar7cfgchanged`.

Addition:\
The special mode can also be configured through `ar7.cfg`. As an example,
here is an excerpt from an Alice configuration:

```
  cpmacspecial {
        enabled = yes;
        normalcfg = "eth0,1,2,3", "eth3,4";
        atacfg = "wan,1", "eth0,2,3", "eth3,4";
    }
```

and another one with `split` interfaces:

```
	cpmacspecial {
		enabled = yes;
		normalcfg = "eth0,1", "eth1,2", "eth2,3", "eth3,4";
		atacfg = "wan,1", "eth1,2", "eth2,3", "eth3,4";
	}
```

Syntax:

```
	modus = portmapping[, ...]

	modus =: normalcfg|atacfg
	portmapping =: "netdevname,portnum[,...]"
  netdevname =: wan|eth[0-3]) (but perhaps also custom names)
  portnum =: [1-4] (as many as the device has)
```

### Beispiel

The four ports should be divided into two groups: LAN 1 and LAN 2 should
be available for the internal network, as `eth0`; LAN 3 and LAN 4 are
connected to two
[Freifunk](http://www.freifunk.net/)-Router
routers that together are in a separate subnet, as *eth1*, and should
therefore be separated from the internal LAN.

Calling `cpmaccfg` without further parameters displays a brief overview of
commands and parameters. This is used to determine which *PORTMASK* to use
for the respective interfaces. This port mask is the logical OR of the
respective port constants. The values are: LAN 1 = 0x01, LAN 2 = 0x02,
LAN 3 = 0x04, LAN 4 = 0x08, and the CPU port is 0x20.

For the example above, the following command must be called:

```
	cpmaccfg ssms eth0 0x23 eth1 0x2c
```

Note that the CPU port is included in both port masks. If this is not
done, the interface is created, but it does not "see" any traffic; not yet
tried, needs verification.

Afterwards, this configuration can be activated with
`cpmaccfg ssm special`.

### Security Warning

During boot, the box always starts in **normal** mode. That means wherever
and however the switch to the desired mode is implemented, for example via
`debug.cfg` or in a Freetz startup script, there is always a certain time
span during which all four ports are in the same layer 2 subnet. Only
after switching do the ports reside in separate layer 2 networks. Only
then must communication happen through layer 3, the IP layer, where any
iptables rules apply, or the internal AVM firewall.

Even before the kernel boots, the bootloader configures the switch as a
normal switch. Changing the configuration in the kernel shortens the time
span somewhat, but does not eliminate the basic problem.

Because no source code is freely available for the bootloader, adapting it
would be difficult.

### Compatibility

-   **FB 7170, Speedports W900V, W701V** These boxes have a built-in
  switch (ADM6996), and `cpmaccfg` works.
-   **7270/3270** Tantos switches: `cpmaccfg` works
    ([Beweis](http://www.ip-phone-forum.de/showpost.php?p=1599909&postcount=23))
-   **Alice IAD 5130, Alice IAD WLAN 3331, FB 5140/3170/2170**
  also work without problems with their current firmware; `cpmaccfg`
  also works.
-   **5124** should also work cleanly.
-   **7050** No switch component is present; these are real network
  interfaces.
-   **7320** like 7050/5050 boxes. These are real network interfaces,
  `eth0` and `eth1`, which can also be configured separately, even
  permanently in `ar7.cfg` in bridge mode.

### Changes 7270v2 vs. 7270v3

On the 7270v3/3270v3, the CPU port moved from bit 5 to bit 0, and the
interface ports moved one bit to the left. For the example above, the
following command must therefore be called on the 7270v3:

```
	cpmaccfg ssms eth0 0x07 eth1 0x19

	# eth0: Maske 0000 0111
	# eth1: Maske 0001 1001

	# 7270v3: 0001 1111               7270v2: 0010 1111
	#                 x---- CPU Port -----------x
	#                x----- Port 1   -----------------x
	#               x------ Port 2   ----------------x
	#              x------- Port 3   ---------------x
	#            x--------- Port 4   --------------x
```


