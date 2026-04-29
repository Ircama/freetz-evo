# fortune 1.2 - DEPRECATED
  - Package: [master/make/pkgs/fortune/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/fortune/)
  - Steward: -

The Fortune computer program is traditionally found on computers running
Unix or Linux operating systems. Similar programs also exist for Windows.
Its function is to display fortune cookies and other humorous aphorisms.
Thanks to
[zyrill](http://www.ip-phone-forum.de/member.php?u=234921)
for this pointless but extremely funny package. This makes the console
fun again.

### Configuring the Package

[![Fortune settings](../screenshots/220_md.png)](../screenshots/220.png)

If the fortune package has been selected in menuconfig, it can be
configured through the web interface. Only the path to the cookies has to
be specified; after saving, the quotes can be enjoyed immediately. Such
fortune files can be found, for example,
[here](http://www.freebsd.org/cgi/cvsweb.cgi/src/games/fortune/datfiles/).

### Showing Fortunes on Console Login

Fortunes are usually started automatically during system startup or login.
The Unix shell command for Fortune is ***fortune***. To do this, the
corresponding commands must be inserted into *.profile* in the user's
HOME directory. This can be done through the Freetz web interface under
*Freetz:.profile*, or from the console in */var/mod/root/.profile*. The
following is sufficient:

```
echo
/usr/bin/fortune
echo
```

After logging in to the box via telnet or ssh, the box greets you with a
randomly selected fortune cookie:

```
   __  _   __  __ ___ __
  |__ |_) |__ |__  |   /
  |   |  |__ |__  |  /_

   The fun has just begun...

BusyBox v1.15.3 (2010-01-21 20:22:22 CET) built-in shell (ash)
Enter 'help' for a list of built-in commands.

determine current TTY
tty is "/dev/pts/0"
console output redirected to this terminal

GRAMMAR IS NOT A TIME OF WASTE
GRAMMAR IS NOT A TIME OF WASTE
GRAMMAR IS NOT A TIME OF WASTE
GRAMMAR IS NOT A TIME OF WASTE

        Bart Simpson on chalkboard in episode AABF10

/var/mod/root #
```

### Further Links

-   [fortune on
    Wikipedia](http://en.wikipedia.org/wiki/Fortune_%28Unix%29)
-   [fortune man
    page](http://linux.die.net/man/6/fortune)
-   [IPPF-Thread](http://www.ip-phone-forum.de/showthread.php?t=196686)

