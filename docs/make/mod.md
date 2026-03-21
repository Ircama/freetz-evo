# Freetz(-MOD)
  - Package: [master/make/pkgs/mod/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/mod/)

- Package source: [make/pkgs/mod](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/mod)

The mod package is the Freetz base package and is always installed.
It provides core system integration and central configuration for features such as:

- swap
- udevmount behavior
- external processing
- Freetz web interface behavior

Note: Depending on your selected configuration, only a subset of options is shown in the UI.

### Swap

A common rule of thumb is to size swap roughly equal to installed RAM.

Swap behavior can be tuned using the swappiness parameter (available since Changeset r6882):

- Lower values keep pages in RAM longer.
- Higher values move pages to swap earlier.

For background details, see [this Linux kernel article](http://lwn.net/Articles/83588/).

Swap is especially useful when running memory-heavy packages such as:

- [PHP](php.md)
- [Tor](tor.md)
- [Transmission](transmission.md)

### Udevmount

- Mountpoint detection method:
  AVM can derive mountpoint names from either device names or partition labels. The currently active method is shown in the UI.

  To switch to LABEL mode:

  ```sh
  ctlmgr -s
  sleep 1
  cat /var/flash/usb.cfg > /tmp/usb.cfg.tmp
  sed 's/volume_labels = .*/volume_labels = yes;/' /tmp/usb.cfg.tmp > /var/flash/usb.cfg
  ctlmgr
  sleep 30
  reboot
  ```

  To switch back to DEVICE mode, change `yes` to `no` in the command above.

- Stop processes blocking unmount:
  During unmount or reboot, blocking processes are detected and Freetz tries to stop them for a clean unmount.

- Auto-run `autorun.sh` and `autoend.sh`:
  If present on a mounted storage device, `autorun.sh` is executed on mount and `autoend.sh` on unmount.

  Enable this only when needed. It can be a security risk.

### get_ip

The `get_ip` script determines the public IP address. It is used by multiple Freetz components and packages.

You can tune the default `get_ip` behavior to your environment. For example, when a FRITZ!Box is used as an IP client or via UMTS, the box often has no direct public IP (NAT). In that case, `--extquery` is typically the relevant method.

The default `--all` still works because it tries multiple methods until one succeeds. If you want faster lookups in this scenario, you can switch from `--all` to `--extquery`.

### Configuration files

### .profile

This file is executed at login. You can define aliases for frequently used commands.

Example:

```sh
alias nl="sed '=' | sed 'N;s/n/t/'"
alias tcpdump6="tcpdump ip6 or proto ipv6"
```

### crontab

The cron daemon runs commands at scheduled times and is configured via `crontab`.

Syntax:

```text
minute | hour | day | month | weekday | command
```

Example:

```text
55  23  * * 7  logger "It is Sunday, 5 minutes before midnight"
*/10  * * * *  logger "Another 10 minutes passed"
* 6,18  * * *  logger "It is 6 o'clock"
```

Unlike typical Linux crontabs, there is no owner/user column. All commands run as `root`.

### dtrace

Commands in this file are triggered by the phone key sequence `#97*3*`.

Example:

```sh
#!/bin/sh
if [ "$(/etc/init.d/rc.lighttpd status)" != "stopped" ]; then
    /etc/init.d/rc.lighttpd stop
else
    /etc/init.d/rc.lighttpd start
fi
```

Visible only when the replace-dtrace patch is enabled.

### hosts

This file maps IP addresses, hostnames, and MAC addresses for DNS and DHCP handling.
See also: [dnsmasq](dnsmasq.md).

Syntax:

```text
<ipaddr>|* <hwaddr>|[id:]<client_id>|* [net:]<netid>|* <hostname>|* [ignore]
```

Example:

```text
192.168.178.20    *                   *  MyPC-1
192.168.178.21    11:22:33:44:55:66   *  MyPC-2
```

### modules

Kernel modules listed in this file are loaded during boot.

Example:

```text
pl2303
ftdi_sio
```

Specify module names without path and without the `.ko` suffix.

### rc.custom

Commands in this file run after boot.

Do not add commands that block in foreground or run for a long time, as this can delay or break startup.

For USB/storage-dependent logic, use `rc.external` instead.

### rc.external

This file is executed after the storage containing [external](../help/howtos/common/external.html) files is mounted, and again before it is unmounted.

Example:

```sh
#!/bin/sh
case "$1" in
    load)
        logger "Storage mounted"
        ;;
    unload)
        logger "Storage unmounted"
        ;;
esac
```

Enable this via:

`Advanced Options` -> `External` -> `Enable external processing`

### shutdown

Commands in this file are executed during system shutdown.

### udev_first / udev_final

Custom rules executed by udev. See [Custom UDEV rules](../patches/custom_udev_rules.html).

