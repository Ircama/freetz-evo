# Freetz Build Process

### Foreword and Motivation

The how-tos contain important information about what *make* targets such
as `menuconfig`, `toolchain`, `precompiled`, `recover`, and others do
when building *Freetz* firmware. Nevertheless, the forum regularly sees
many questions about the build process, usually when the process does not
complete and the user does not know why. The reason is usually that the
user is inexperienced with
[GNU make](http://www.gnu.org/software/make/) keine
because, firstly, they are not a C/C++ programmer and/or, secondly, the
Linux command line itself is already a sealed book to them. At least the
first point also applies to me, so I read up superficially in order to
understand the *Freetz* `Makefile` better, or at all. I document the
result of my work here.

The problems of those seeking help in the forum do not end with the build
sometimes getting stuck. Since many questions sound "stupid" from the
experts' point of view and are repeated often, not everyone is skilled at
using the forum search or Google and some are simply lazy, the questions
become annoying to some professionals. The answers are then correspondingly
short, which in turn leads to follow-up questions and more clutter in the
forum. When the person seeking help has then fixed the cause of the
problem, by installing a Linux package, selecting or deselecting the right
option in `make menuconfig`, or installing a patch, they often still
cannot get the build running again because dependencies are not maintained
perfectly and they would first need to call *xy-clean* and/or
*xy-precompiled*, but nobody told them because it is also hard to predict.

The dream of a perfect `Makefile` that, after every file change, does
exactly the minimum necessary to build the current target is theoretically
achievable, but not realized here. It must be said, however, that the
Freetz *make* process is already relatively good, just not foolproof. That
was probably not the goal either, because a "fool" should not want to
build firmware for their DSL router. On the other hand, it is good for
our community if the learning curve for new members is made a little more
pleasant. It makes no sense for everyone to reinvent the wheel and work
everything out for themselves just because others had to do so earlier.

### Basics

This documentation is based on **Freetz 1.1.4**. Since newer Freetz
versions now exist, differences are noted in a few places.

### What Does make Do?

That would really exceed the scope here, so just a few links. Reading up
is worthwhile; education is never wasted:

-   [Wikipedia article about Make](http://de.wikipedia.org/wiki/Make)
-   [An introduction to
    Makefiles](http://www.ijon.de/comp/tutorials/makefile.html)
    (German, short and concise, easy to understand)
-   [Recursive Make Considered
    Harmful](http://members.tip.net.au/~millerp/rmch/recu-make-cons-harm.html)
    (very exciting for advanced users and philosophers, PDF download)
-   [Wikipedia article about
    Autoconf](http://de.wikipedia.org/wiki/GNU_autotools)
    (not used by *Freetz* itself, but by various packages)

### What Does Freetz Consist Of?

The modified firmware is assembled from several components:

-   **Original firmware**, consisting of Linux kernel and filesystem. It
    forms the basis and framework for the mod. Many beginners mistakenly
    assume that the original firmware is discarded and completely replaced
    by something self-built. That is not the case. Many important parts
    are taken over as they are and extended with new functions, or
    individual parts are specifically replaced. Important components of the
    original firmware are:
    -   **Kernel** (formerly 2.4, currently 2.6). For Daniel's mod, a 2.4
        kernel could be reused; for Freetz, it must be replaced by a
        self-built 2.6 kernel. If original firmware with a 2.6 kernel is
        used as the basis, that kernel can be reused or optionally
        replaced as well.
    -   **Filesystem** with standard UNIX tools and AVM-specific tools,
        such as the web interface. It is taken over almost unchanged with
        one important exception; see the next point.
    -   **Busybox**: collection of the most important command-line tools,
        optimized for embedded systems and contained in a single
        executable file. The individual tools are implemented through
        symbolic links to
        [Busybox](http://de.wikipedia.org/wiki/Busybox)
        under seemingly independent names.

After unpacking the corresponding archive, for example
`freetz-1.1.4.tar.bz2`, **Freetz** itself looks like the following list,
sorted alphabetically, not by importance. The subdirectories `build`,
`packages`, and `source` are created only during the first *make* run.

-   **Root directory**: contains several configuration files, more on that
    later, as well as changelog, firmwares, and readme. There are also
    various subdirectories:
    -   ***addon***: static and theoretically dynamic packages, already
        compiled, are unpacked here if they should be included in the
        firmware filesystem and go beyond the standard mod's delivery
        scope.
    -   ***build***: the original firmware image is unpacked into
        *build/original*. The three individual components are then in the
        subdirectories *kernel* (Linux kernel), *filesystem* (root
        filesystem), and *firmware* (tools contained at the top level of
        the firmware image and required for its installation). As already
        mentioned, these components are woven together with generated
        components such as kernel, Busybox, packages, and others, and
        stored in the parallel directory structure *build/modified*. From
        there they are then taken to finally pack the firmware image with
        *tar*.
    -   ***busybox***: storage location of the newly built Busybox for the
        mod. Starting with Freetz 1.2 it is found under
        `packages/target-mips(el)_uClbic-$(uClibc-Version)/busybox`.
    -   ***dl***: downloads of source and binary packages for toolchain
        and mod. With a few exceptions, package web interfaces are
        contained directly in the mod; other files are downloaded from the
        internet during the build using *wget*.
    -   ***favicon***: currently contains two small sets of favicons that
        can be selected via `make menuconfig` to give the Freetz web
        interface nice small browser icons, displayed in the address bar
        and bookmarks.
    -   ***howtos***: a few short German and English guides for building
        the mod or custom extensions.
    -   ***kernel***: storage location of the newly built Linux kernel and
        its modules for the mod.
    -   ***make***: for each package, this contains the include files and
        configuration data for the large `Makefile` in the root directory,
        as well as startup scripts, CGI files, and other files belonging
        to the package. The configuration data also contains the version
        numbers of packages downloaded into *dl*.
    -   ***packages***: built packages are stored here. In one
        subdirectory per package, as under `make`, the corresponding
        binary and configuration data are located and woven into the
        filesystem, visible under `build/modified`; compare the previous
        point. Starting with Freetz 1.2, an additional directory level is
        added under `packages/`, separating by big or little endian and
        uClibc version.
    -   ***patches***: patches that are applied to the sources after
        unpacking, depending on which hardware and/or configuration
        setting is used.
    -   ***root***: image of the future firmware root filesystem. Web
        pages, startup scripts, configuration data, and so on are located
        here. During firmware building, they are woven together with the
        original data and additional generated files such as kernel and
        Busybox into a complete image.
        -   Freetz 1.2: the directory was moved to `make/mod/files/root`
            for unification.
    -   ***source***: all source texts for toolchain, AVM GPL package,
        tools, packages, Busybox, and kernel are unpacked here so the
        corresponding build processes can run over them afterwards.
        -   Freetz 1.2: to achieve better separation and avoid unnecessary
            *make dirclean*s, the sources are split as follows:
            -   ***host-tools***: tools for the host are built here, such
                as busybox, mksquashfs, fakeroot, and so on.
            -   ***kernel***: kernel sources.
            -   ***target-mips(el)_uClibc-$(uClibc-Version)***: selected
                packages are unpacked and built here.
            -   ***toolchain-mips(el)_gcc-$(GCC-Version)_uClibc-$(uClibc-Version)***:
                toolchain sources and build. Depending on menuconfig
                selection, contains binutils, ccache, gcc, gdb, uClibc,
                and libtool.
    -   ***toolchain***: after unpacking the mod, the *Makefile* includes
        for building the toolchains are located here. A toolchain in
        general is a collection of tools required to build software, such
        as compilers and linkers. In our case, there are two separate
        toolchains: one for building the kernel (`gcc-3.4.6`) and one for
        the remaining targets (`gcc-4.2.1-uClibc-0.9.28/0.9.29`). The
        toolchains are then built into corresponding subdirectories.
        Building the toolchains is optional because precompiled versions
        are available for download. Depending on host speed, building the
        toolchain can take 20 to 60 minutes.
        -   Freetz 1.2: the GCC versions were updated to current versions
            at the time, gcc-4.4.6, gcc-4.5.3, and gcc-4.6.0.
    -   ***tools***: additional tools and their `Makefile` includes are
        located here, required for building firmware images or for
        `make recover`. The tools are used, for example, to unpack the
        original firmwares, SquashFS filesystem, and to repack the later
        mod images after all components have been woven in. An older tar
        version (15.1), which creates firmware archives compatible with
        the unpackers contained in the original firmwares, is included
        among other helpers.
        -   Freetz 1.2: the tar package is no longer built as a tool.
            Depending on the task, host tar or busybox tar is used.

### Build Process Flow

It should be generally known that the three most important make targets,
to be called in this order, are:

-   `make menuconfig` - interactively assemble packages, select
    additional libraries, save configuration.
-   `make` - build tools, build toolchains unless an external compiler was
    selected, then build libraries, Linux kernel, and packages, and
    finally build firmware.

In addition, there is a considerable number of other make targets, some
of which are not directly visible in the Makefile but are generated by
automated substitution processes. This has the advantage that, for
example, each package has the same sub-targets, so a *make* call can
always directly affect individual packages, for example clean up or build
again. If `make precompiled`, for example, got stuck in package `mc`
because a Linux package required for building was missing in the
distribution and first had to be installed with the package manager, a
new call to the global *precompiled* target may still not complete because
there are inconsistencies in the package build. A sequence such as
`make <package>-clean`, `make <package>-precompiled`, for example
*mc-clean* and *mc-precompiled*, usually helps. Package names can be seen
from the names of the subdirectories in the `make` directory.

### Include Chain

In general, there are two ways to use *make* for hierarchically structured
builds. The traditional one uses a `Makefile` in the main directory and
another `Makefile` in each subdirectory. That this is not a good idea is
convincingly explained in
[Recursive Make Considered
Harmful](http://members.tip.net.au/~millerp/rmch/recu-make-cons-harm.html)
. The good news is that Freetz uses the second method: include files in
the subdirectories. That means the `Makefile` dynamically loads the
includes required for the current target and thus creates a single large
virtual `Makefile`, which is then processed. This is nice, but it means
that in the `Makefile` we see things being called and processed whose
origin is not quite so easy to determine unless the directory structure is
examined in detail. I try to make this a little more transparent here.

-   First, the `Makefile` includes the configuration file `.config` in the
    main directory. It contains the options set in `make menuconfig` for
    assembling the firmware image. This already makes clear why
    `make menuconfig` should always be called first. Incidentally, the
    file does not exist immediately after unpacking the mod archive. There
    is an exception to the include: if only targets from the group
    *menuconfig, config, oldconfig, defconfig, tools* are to be built, no
    include happens here because those targets do not need it.
-   A little later, `tools/make/Makefile.in` and `tools/make/*.mk` are
    included, causing the individual tool targets, such as
    *find-squashfs, lzma, squashfs, tichksum, makedevs, fakeroot*, to be
    added to the variable *TOOLS*. Afterwards, a list of sub-targets is
    generated for each tool target:
    -   ***<tool>***: builds the tool.
    -   ***<tool>-source***: unpacks the source files so the tool can be
        built afterwards.
    -   ***<tool>-clean***: calls the tool's own `Makefile` in the tool
        subdirectory with `make clean`. The *clean* target usually deletes
        all generated files and directories so a clean rebuild is possible.
    -   ***<tool>-dirclean***: deletes the entire tool subdirectory. This
        is useful when unpacking a newer version and wanting to remove the
        old one completely first.
    -   ***<tool>-distclean***: deletes the distribution directory inside
        the tool subdirectory, where the built files lie ready for
        installation.
-   Now `.config.cmd` is processed. This recursively reads configuration
    switches of various packages that are later available to the build.
-   Now things really get going: including `make/pkgs/Makefile.in`,
    `make/pkgs/*/Makefile.in`, `make/toolchain/Makefile.in`, and the
    corresponding ***\*.mk*** files adds even more information to the
    virtual `Makefile`. Afterwards, analogously to the tools above, the
    following targets are available, divided into the groups *TARGETS,
    PACKAGES, LIBS, TOOLCHAIN*:
    -   ***<target>-precompiled***: builds a target that does not belong
        to a package, the library target group, or the toolchain. Examples
        include the Linux kernel, the CGI mod (Freetz web interface),
        Busybox, the CGI tool Haserl (currently not a package), iptables,
        and the AVM GPL sources.
        -   Freetz 1.2: only the kernel and Busybox count as targets.
    -   ***<target>-source***: unpacks the source files so the target can
        be built afterwards.
    -   ***<target>-clean***: calls the target's own `Makefile` in the
        target subdirectory with `make clean`. The *clean* target usually
        deletes all generated files and directories so a clean rebuild is
        possible.
    -   ***<target>-dirclean***: deletes the entire target subdirectory;
        useful when unpacking a newer version and removing the old one
        completely first.
    -   ***<package>-precompiled***: builds a package.
    -   ***<package>-source***: unpacks the source files so the package
        can be built afterwards.
    -   ***<package>-clean***: calls the package's own `Makefile` in the
        package subdirectory with `make clean`. The *clean* target usually
        deletes all generated files and directories so a clean rebuild is
        possible.
    -   ***<package>-dirclean***: deletes the entire package
        subdirectory; useful when unpacking a newer version and removing
        the old one completely first.
    -   ***<package>-list***: adds the package either to the list of
        static or dynamic packages.
    -   ***<lib>-precompiled***: builds a library, for example ncurses,
        libgcrypt, or OpenSSL.
    -   ***<lib>-source***: unpacks the source files so the library can be
        built afterwards.
    -   ***<lib>-clean***: calls the library's own `Makefile` in the
        library subdirectory with `make clean`. The *clean* target usually
        deletes all generated files and directories so a clean rebuild is
        possible.
    -   ***<lib>-dirclean***: deletes the entire library subdirectory;
        useful when unpacking a newer version and removing the old one
        completely first.
    -   ***<toolchain>***: builds the toolchains, kernel and target
        toolchain.
    -   ***<toolchain>-source***: unpacks the source files so the
        toolchain can be built afterwards.
    -   ***<toolchain>-clean***: calls the toolchain's own `Makefile` in
        the toolchain subdirectory with `make clean`. The *clean* target
        usually deletes all generated files and directories so a clean
        rebuild is possible.
    -   ***<toolchain>-dirclean***: deletes the entire toolchain
        subdirectory; useful when unpacking a newer version and removing
        the old one completely first.
    -   ***<toolchain>-distclean***: deletes the distribution directory in
        the toolchain subdirectory.
-   In the previous step, two more targets were added, making it possible
    to customize two central parts of the firmware even more
    individually:
    -   ***kernel-menuconfig***: the Linux kernel also has a nice
        configuration interface where many things can be set. Personally,
        I do not recommend changing anything here unless you really know
        what you are doing. It becomes very difficult to find help in the
        forum if your kernel is configured differently from everyone
        else's.
    -   ***busybox-menuconfig***: Busybox can also be extended with
        features in various places at the cost of size. Owners of 8 MB
        boxes, such as the 7170, usually still have enough space to add a
        feature or two here. I recommend not omitting anything included by
        default, so comparability in forum discussions remains. It is no
        use disabling the *Gunzip* feature in *Tar* and then asking in the
        forum why a *Gzip* archive could not be unpacked. On the other
        hand, enabling *Bunzip2* additionally is not very disturbing,
        because it is only an add-on without side effects, as far as human
        judgment can tell.

### Other Make Targets

Further targets are contained directly in the top-level `Makefile`, so
they are not included from elsewhere.

-   Some of them are **helper targets**, rarely called manually because
    they are mainly intended for use by higher-level targets. Examples are
    *config, oldconfig, defconfig*.
-   There is also the utility target ***recover***, with which a broken
    box can be revived; details would exceed the scope of this article.
-   There are also **aggregate targets** such as *sources, precompiled,
    libs, packages-precompiled*, which call a whole group of similarly
    named or purpose-related sub-targets.
-   If you only want to assemble firmware and all necessary preliminary
    work for it, such as building toolchains and `make precompiled`, has
    already been done, you can use the target ***firmware***. It builds
    the tools if needed, not to be confused with toolchains, and then gets
    to work. At the end you have a firmware image in the `images`
    directory named *\*.image*. This target is called implicitly when you
    simply call `make`, thus building the default target. Incidentally, the
    script `fwmod` in the root directory does all the work of firmware
    building. It is certainly interesting to look at this script in detail
    if you want to know what happens there.

So, I hope this article helps one or another modder. Discussions,
feedback, and corrections are welcome as always and can be added in the
related
[Forums-Thread](http://www.ip-phone-forum.de/showthread.php?t=129115)
.

[Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)\
Revised by Oliver Metz


