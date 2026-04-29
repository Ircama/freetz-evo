# dtach 0.9 (binary only)
  - Homepage: [https://dtach.sourceforge.net/](https://dtach.sourceforge.net/)
  - Changelog: [https://github.com/crigler/dtach/tags](https://github.com/crigler/dtach/tags)
  - Repository: [https://github.com/crigler/dtach](https://github.com/crigler/dtach)
  - Package: [master/make/pkgs/dtach/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/dtach/)
  - Steward: -

*"dtach is a free (GPL'ed) program for POSIX-compliant OSs intended to
provide similar functionality to that of the GNU Project's Screen, but
stripping out what the developer (Ned T. Crigler) considers to be
unneeded features to provide a much slimmer product; in addition, it is
intended to interfere less with key bindings than Screen does."*
(source: Wikipedia - see below)

*Dtach* is a tiny program that emulates the detach feature of
*[screen](screen.md)*, allowing you to run a program in an
environment that is protected from the controlling terminal and attach
to it later. It was introduced in Freetz trunk
Changeset r2636
by whoopie. It is smaller than the aforementioned *screen*.

### Usage

Create a new dtach session, using [mcabber](mcabber.md) as an example:

```
dtach -c /tmp/mcabber.dtach mcabber
```

Create a new dtach session but immediately leave the session again, or
start it in the background:

```
dtach -n /tmp/mcabber.dtach mcabber
```

Use "*Ctrl + *" to leave the session.

Attach to the session again:

```
dtach -a /tmp/mcabber.dtach
```

### Further Links

-   [Sourceforge project page
    (English)](http://dtach.sourceforge.net)
-   [Wikipedia
    (English)](http://en.wikipedia.org/wiki/Dtach)
-   [Thread for discussion in
    IP-Phone-Forum.de](http://www.ip-phone-forum.de/showthread.php?t=176923)

