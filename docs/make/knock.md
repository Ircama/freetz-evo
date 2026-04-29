# Knock 0.8 - DEPRECATED
  - Homepage: [https://www.zeroflux.org/projects.html](https://www.zeroflux.org/projects.html)
  - Manpage: [https://linux.die.net/man/1/knockd](https://linux.die.net/man/1/knockd)
  - Changelog: [https://github.com/jvinet/knock/blob/master/ChangeLog](https://github.com/jvinet/knock/blob/master/ChangeLog)
  - Repository: [https://github.com/jvinet/knock](https://github.com/jvinet/knock)
  - Package: [master/make/pkgs/knock/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/knock/)
  - Steward: -

*"Knock, and it shall be opened unto you"* could be this package's
caption. *knockd* provides a good way to start services remotely. If the
very resource-friendly Knock daemon is running on the Fritzbox, the
correct "knock signal" can indicate, with suitable configuration, that
you want to get in. When the correct "knock code" has been sent, knockd
starts the associated program, for example the SSH daemon. Another knock
can stop it again later. This approach provides additional security
because ports are open only when they are really needed, so a hacker's
port scan usually comes up empty.

### Further Links

-   [A short workshop on
    knockd](http://wiki.hetzner.de/index.php/Knockd)
-   [Article on
    "Portknocking"](http://blog.roothell.org/archives/146-Portknocking-Tools-Teil-1-knockd.html)
-   [Knockd demo on
    YouTube](http://www.youtube.com/watch?v=EbzrLPf6D7Y)

