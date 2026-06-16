# ltrace 0.7.3-git/0.8.1 (binary only)
  - Homepage: [https://www.ltrace.org/](https://www.ltrace.org/)
  - Manpage: [https://linux.die.net/man/1/ltrace](https://linux.die.net/man/1/ltrace)
  - Changelog: [https://gitlab.com/cespedes/ltrace/commits/main](https://gitlab.com/cespedes/ltrace/commits/main)
  - Repository: [https://gitlab.com/cespedes/ltrace](https://gitlab.com/cespedes/ltrace)
  - Package: [master/make/pkgs/ltrace/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ltrace/)
  - Steward: -

**[ltrace](http://ltrace.alioth.debian.org/)** is
a debugging tool that can monitor library calls triggered by a program
as well as all received signals. A comparable tool is available in the
[strace](strace.md) package.

### Using ltrace to inspect ctlmgr
From @LizenzFass78851 in [Juis for devices HWR277+](https://github.com/orgs/Freetz-NG/discussions/1415#discussioncomment-17296891)

- Disable the AVM watchdog

```bash
echo disable > /dev/watchdog
```

- Stop ctlmgr and let it restart

```bash
kill -9 $(pidof ctlmgr)
ctlmgr
```

- Access the Web UI via HTTP only until the update screen appears

- Create an ltrace configuration template

```bash
nano /var/mod/etc/ltrace.conf
```

With the following content **(updated)**

```c
int avmssl_write(void*, string, int, void*);
int avmssl_read(void*, +string, int, int);
```

- Start ltrace (tested with ltrace 0.8.1)

```bash
ltrace -F /var/mod/etc/ltrace.conf -s 8192 -e avmssl_write+avmssl_read -p $(pidof ctlmgr)
```

- Click on "Check for updates" in the Web UI

- The output will appear

### Further Links

  - [Repository der alten Version](https://github.com/dkogan/ltrace)


