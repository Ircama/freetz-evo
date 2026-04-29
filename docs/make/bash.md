# bash 3.2.57 (binary only) - DEPRECATED
  - Package: [master/make/pkgs/bash/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/bash/)
  - Steward: -

The **B**ourne **A**gain **Sh**ell is a
[Unix
shell](http://de.wikipedia.org/wiki/Unix-Shell), or, put another way, a
"command-line interpreter" for Unix and Linux systems. *Bash* is not just
any shell, but probably the most widely used one, and is therefore found
on almost all Unix/Linux systems. *Bash* is part of the
[GNU
project](http://de.wikipedia.org/wiki/GNU-Projekt).

The name was chosen to be intentionally ambiguous. *Bash* is fully
compatible with the original *Bourne Shell* (sh), so it can mean "Bourne
shell again" or the "born-again shell". Others derive the name from the
verb "to bash" or from the noun "bash" (celebration, party, hit)...

As already mentioned, Bash is available for many systems: Unix systems,
Linux,
[Cygwin](http://de.wikipedia.org/wiki/Cygwin),
[MSYS](http://de.wikipedia.org/wiki/MSYS), and even
[Microsoft Windows Services for
UNIX](http://de.wikipedia.org/wiki/Microsoft_Windows_Services_for_UNIX)
are included. And, with this package, of course also the Freetz box.

Note: the manual prompt adjustment described below has no longer been
necessary since
Changeset r5803 (freetz-devel)
because it is already built in there.

The so-called prompt, i.e. what is displayed before the cursor, can be
customized. To do this, adjust the PS1 variable, which can be done very
conveniently through the Freetz WebGUI under Settings/.profile. Bash
knows, among others, the following variables for PS1:

```
h : Host name
H : Host name including domain
d : Date
t : Time
u : User login name
w : Working directory, current working directory
l : Terminal name, for example tty1
# : Input line number
 : The character ""
```

This makes it possible, for example, to show the user and host name in
the prompt in addition to the current path:

```
export PS1="u@h w $ "
```

The result with the example above then looks like this:

```
root@fb1 /var/mod/root $
```

The host (the Fritzbox) is named exactly as specified in the variable
/proc/sys/kernel/hostname, here "fb1" (the default is "fritz.box").

Ash
===

This works both for bash, installed with this package, and for ash, the
default in Freetz without an additional package. ash supports only the
following:

```
h : Host name
u : User login name
w : Working directory, current working directory
# : Input line number
```

### Bash as Login Shell

TODO

### Further Links

-   [Wikipedia article](http://de.wikipedia.org/wiki/Unix-Shell#Die_Bourne-Again-Shell)
-   [English Wikipedia
    article](http://en.wikipedia.org/wiki/Bash) with
    more extensive details
-   [Homepage of
    Bash](http://www.gnu.org/software/bash/bash.html)
-   [Bash
    Guide](http://tldp.org/LDP/Bash-Beginners-Guide/html/index.html)
    for Beginners
-   [ABS](http://tldp.org/LDP/abs/html/index.html) -
    the **A**dvanced **B**ash **S**cripting Guide
-   [Bash Online Forum](http://bashscripts.org/)
-   [bash - the Bourne again shell in
    LinuxWiki](http://linuxwiki.de/Bash)

