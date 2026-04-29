# hd-idle 0.99 - DEPRECATED
  - Package: [master/make/pkgs/hd-idle/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hd-idle/)
  - Steward: -

**[hd-idle](http://hd-idle.sourceforge.net/)** is
a tool for spinning down external hard disks after a configured idle
time. Because most external IDE hard-disk enclosures do not allow an
idle timer to be set directly, a utility such as *hd-idle* (or the
*[spindown-CGI](spindown.md)* package also available in Freetz) is
needed for this job.

Depending on the manufacturer, there are three different power modes:

```
active/idle (normal operation)
standby (low power mode, drive has spun down)
sleeping (lowest power mode, drive is completely shut down)
```

