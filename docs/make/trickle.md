# trickle 1.07 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/trickle/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/trickle/)
  - Steward: -

**trickle** is a lightweight bandwidth shaper that can be used with
trickled or in standalone mode. With trickle, it is possible to define
which bandwidth an application may use. This keeps the internet
connection usable for other programs, for example telephony, even during
large [downloads](../Download.html). Traffic is regulated through its own
dynamic library (trickle-overload.so), which is loaded by trickle at
startup. trickle can throttle only TCP connections. trickle does not
require root privileges. trickle can be used only with dynamically linked
applications. To throttle the bandwidth of statically linked
applications, trickle should be used with a proxy, such as Privoxy or
ffproxy, and the statically linked applications should be forced, for
example with iptables, to use that proxy. With multi-user operation on
the box, trickle should also be used with a proxy. With trickle, the load
on the box can also be kept under control, because lower bandwidth also
uses less memory and less CPU power. This can prevent the box from
rebooting. With trickle, incoming and outgoing network traffic can be
controlled so that both the line and the box are used optimally.

### Syntax

```
Usage: trickle [-hvVs] [-d <rate>] [-u <rate>] [-w <length>] [-t <seconds>]
               [-l <length>] [-n <path>] command ...
        -h           Help (this)
        -v           Increase verbosity level
        -V           Print trickle version
        -s           Run trickle in standalone mode independent of trickled
        -d <rate>    Set maximum cumulative download rate to <rate> KB/s
        -u <rate>    Set maximum cumulative upload rate to <rate> KB/s
        -w <length>  Set window length to <length> KB
        -t <seconds> Set default smoothing time to <seconds> s
        -l <length>  Set default smoothing length to <length> KB
        -n <path>    Use trickled socket name <path>
        -L <ms>      Set latency to <ms> milliseconds
        -P <path>    Preload the specified .so instead of the default one
```

```
Usage: trickled [-hvVfs] [-d <rate>] [-u <rate>] [-t <seconds>] [-l <length>]
                [-p <priority>] [-c <file>] [-n <path>] [-N <seconds>]
                [-w <length>]
        -h            Help (this)
        -v            Increase verbosity level
        -V            Print trickled version
        -f            Run trickled in the foreground
        -s            Use syslog instead of stderr to print messages
        -d <rate>     Set maximum cumulative download rate to <rate> KB/s
        -u <rate>     Set maximum cumulative upload rate to <rate> KB/s
        -t <seconds>  Set default smoothing time to <seconds> s
        -l <length>   Set default smoothing length to <length> KB
        -p <priority> Set default priority to <priority>
        -c <file>     Use configuration file <file>
        -n <path>     Set socket name to <path>
        -N <seconds>  Notify of bandwidth usage every <seconds> s
        -w <length>   Set window size to <length> s
```

### Examples for Using trickle

**1. Through a proxy:**

```
trickle -s -u 20 -d 100 /var/mod/etc/init.d/rc.privoxy start
```

```
wget -e "http_proxy = http://192.168.127.253:8118" http://speedtest.netcologne.de/test_10mb.bin
--2010-02-21 10:07:58--  http://speedtest.netcologne.de/test_10mb.bin
Connecting to 192.168.127.253:8118... connected.
Proxy request sent, waiting for response... 200 OK
Length: 10485760 (10M) [application/octet-stream]
Saving to 'test_10mb.bin'.
100%[==========================================================================================================================================>] 10.485.760  20,2K/s   in 8m 53s
2010-02-21 10:16:51 (19.2 KB/s) - 'test_10mb.bin' saved [10485760/10485760]
```

**2. Directly on the application:**

```
trickle -s -u 50 -d 70 wget http://speedtest.netcologne.de/test_10mb.bin
--2010-03-06 22:54:02--  http://speedtest.netcologne.de/test_10mb.bin
Resolving speedtest.netcologne.de... 87.79.12.103, 87.79.12.102
Connecting to speedtest.netcologne.de|87.79.12.103|:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 10485760 (10M) [application/octet-stream]
Saving to: `test_10mb.bin.1'

100%[==========================================================================================================================================>] 10,485,760  52.6K/s   in 2m 59s

2010-03-06 22:57:00 (57.4 KB/s) - `test_10mb.bin.1' saved [10485760/10485760]
```

**Load on the box (from top):**

```
2660  1901 root     S     3028  10%   2% wget http://speedtest.netcologne.de/test_10mb.bin
```

**Search keywords:** traffic, bandwidth, shaping, shaper, limiter,
throttling, bandwidth limiting, bandwidth, throttle, limit

### Further Links

[trickle](http://monkey.org/~marius/pages/?page=trickle)

[Article in
linuxuser](http://www.linux-user.de/ausgabe/2005/11/056-trickle/index.html)

[manpage
trickle](http://monkey.org/~marius/trickle/trickle.1.txt)

[manpage
trickled](http://monkey.org/~marius/trickle/trickled.8.txt)

[manpage
trickled.conf](http://monkey.org/~marius/trickle/trickled.conf.5.txt)

[trickle at
Debian](http://patch-tracker.debian.org/package/trickle/1.07-9)

