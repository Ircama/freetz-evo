# How Do I Build My Own Package for Freetz?

Note: this article mixes two different questions:

-   How do I write my first program?
-   How do I integrate an existing program as a package in Freetz?

The second question is already covered elsewhere. If there is interest in
the first question, it should be split out accordingly. Usually, finished
programs are integrated into Freetz rather than being written completely
from scratch. [GNU Hello](http://ftp.gnu.org/gnu/hello/hello-2.3.tar.gz)
may be a better basis for a more complex program because it also creates a
`configure` file with automake. (ralf)

Because this is my first wiki entry, please bear with me if not
everything looks exactly as it should yet.

To create a package for Freetz myself, I first had to find a suitable
"project" with source code that could actually be compiled for the
FRITZ!Box.

During the search, I found the
[HTTP Tunnel Server](http://www.nocrew.org/software/httptunnel.html).
With *httptunnel*, TCP connections can be tunneled over HTTP, allowing
access to the FRITZ!Box even through very restrictive proxies. More about
this can be read [here](http://linuxwiki.de/HttpTunnel).

The evolution of my experience, enriched by many helpful tips and notes
from Linux experts and developers in the forum, can be read in
[this thread](http://www.ip-phone-forum.de/showthread.php?t=167980),
which is also the right place for further questions and discussion.

I used the following environment to build the package:

-   FRITZ!Box 7170 with Freetz 1.0
-   StinkyLinux 1.06 in a VM on a MacBook

There are other environments for building firmware or Freetz packages;
they are described elsewhere.

The how-tos contain important information about what *make* targets such
as `menuconfig`, `toolchain`, `precompiled`, `recover`, and others do
while building Freetz firmware. That information is worth reading if you
want to understand exactly what happens when building firmware or a new
Freetz package, even though I only read it afterwards (mea culpa).

A very good guide can be found elsewhere.

There is a small [demo package (demopackagea)]{.underline}. More about it:

DemoPackageA, a "Hello World" demo package:
[forum post including download](http://www.ip-phone-forum.de/showthread.php?t=177052).

[Short guide for adapting an existing package]{.underline}

-   Assume a build system exists. This can be the StinkyLinux mentioned
    above with Freetz checked out. All directories mentioned here are
    inside the Freetz folder, which is represented by `/` in this short
    guide.
-   There is a compact package named `empty`. This is a real package that
    can be used as a template. Take a look at it:
    `freetz.folder/make/empty/*`.
-   Think of a short, clear name for your package.
-   Create a directory inside `make`. This directory should have the same
    name as the package; below it is called the package directory.
-   Copy `empty.mk` from the `empty` package into the package directory
    and rename it. The name of this file determines the package name.
-   Adapt `package.mk` as well. It should no longer contain `empty` in any
    capitalization. Set the version to `0.0.01`. The `SITE` entry is not
    relevant as long as the file is in `/dl`. If the file is offered for
    download later, the corresponding value must be entered here.
-   Adapt `Config.in` and `Makefile.in`, but do not rename them.
-   To make the package visible through `make menuconfig`, add it to
    `/make/Config.in`, similar to how package `empty` is listed. For a
    new package, the `Testing` section is appropriate at first.
-   Run `make menuconfig` and select the package.
-   Freetz now knows the package, but it still needs to be built. This
    mini package consists of two files, `pluginName.c` and `Makefile`.
-   Create a directory anywhere; it will be deleted again shortly. The
    directory name must be `pluginName-Version`, for example version
    `0.0.01`.
-   Create `pluginName.c` in this directory with this content:
    ::: {.code}
        /*  "plugin_name".c Version:0.0.01  */
        #include <stdio.h>

        main(){
         printf("Hello World \n");
        }
    :::

-   Create the file `Makefile` in this directory with this content:

    ```
    BINARY=plugin_name
    OBJS=plugin_name.o

    all: $(BINARY)

    $(BINARY): $(OBJS)

    clean:
        $(RM) $(BINARY) $(OBJS)
    ```

-   Change one directory level down.
-   Create a `tgz` archive; the directory can be deleted afterwards:
    `tar cfz plugin-0.0.01.tgz plugin-0.0.01`.
-   Copy the `tgz` archive into `/dl`.
-   The package can now be built for the first time with
    `make Packagename-precompiled` from `/`.

To be continued...


