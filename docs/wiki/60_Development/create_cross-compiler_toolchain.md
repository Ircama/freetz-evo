# Create a Cross-Compiler / Toolchain

Creating a cross-compiler with Freetz is very simple:

1.  Run `make menuconfig`. Under *Advanced options -> Compiler options*,
    select the options for the cross-compiler. If the compiler should
    compile programs for firmware created with Freetz, usually nothing
    needs to be changed. If the compiler should compile for original
    firmware, select the corresponding configuration under "uClibc config".
    
    **Warning:** In the second case, this unpacked Freetz instance should
    no longer be used to create images. Use only the cross-compiler itself
    from it.
2.  Required packages are
    [gcc](http://de.wikipedia.org/wiki/GNU_Compiler_Collection),
    [binutils](http://de.wikipedia.org/wiki/GNU_Binutils),
    [make](http://de.wikipedia.org/wiki/Make),
    [bison](http://en.wikipedia.org/wiki/GNU_bison),
    [flex](http://en.wikipedia.org/wiki/Flex_lexical_analyser)
    and
    [texinfo](http://de.wikipedia.org/wiki/Texinfo):
    `make toolchain`\
    After quite some time and about 2 GB, two cross-compilers have been
    created:
    -   `./toolchain/kernel/bin/*-unknown-linux-gnu-gcc` :
        cross-compiler for the kernel sources
    -   `./toolchain/target/bin/*-linux-uclibc-gcc` : cross-compiler for
        userspace programs
3.  `make libs` builds all libraries selected in `menuconfig` and installs
    their headers.

## Create Your Own Download Toolchain

Since changeset r9983:

You can build your own toolchains and use them as download toolchains by
overriding the corresponding options under "Override options/Override
precompiled toolchain options":

1.  activate "Toolchain options/Build own toolchains"
2.  set toolchain related options to the desired ones under "Toolchain
    options"
3.  (optional) make your own modifications under
    \$(freetz_root)/toolchain
4.  call "make KTV=freetz-\${MY_VERSION}-\${MY_SUFFIX}
    TTV=freetz-\${MY_VERSION}-\${MY_SUFFIX} toolchain"
5.  wait for the build to complete
6.  (optional) upload the created download toolchain files to a site

The toolchains created in steps above can then be reused:

7.  activate "Toolchain options/Download and use precompiled
    toolchains"
8.  activate "Override options/Override precompiled toolchain options"
9.  set version/suffix/md5/download-site values to the values used in
    the steps above
10. adjust gcc/uClibc versions under "Toolchain options" and set them to
    the same values as in step 2

## Create a Target/Native Compiler Toolchain

Sometimes it is easier to use native development tools and a compiler
directly on the FRITZ!Box: run `./configure`, build dependent libraries,
test the resulting binaries directly on the box, and find configure
options for packages that do not work well with cross-compiling. In terms
of performance, compiling is already possible on a 7270 box.

### General Prerequisites

-   connect an external USB drive with an additional swap and ext3
    partition
-   add a directory or mountpoint `/usr/local`, easily created with the
    addon package, pointing to your writable USB drive. This can be done
    with a mount command executed by `autorun.sh` through the Freetzmount
    mechanism, for example:
    `mount -o /var/InternerSpecher/uStor03/local /usr/local`

### Create the Matching Target Compiler and Libraries

-   select Level of user (Expert), then select Toolchain options -> Build
    binutils and gcc for target, and select needed libraries in Shared
    libraries
-   select BusyBox applets -> developer tools and the make binaries
-   build the Freetz image, copy some required libraries to the addon
    package, and rebuild the image\
    `cp -R toolchain/target/target-utils/lib addon/own-files-0.1/root`
-   archive the cross-compiled native binaries, unpack them on the box
    into `/usr/local`, and correct some links:\
    `tar -cf ~/compiler.tar -C toolchain/target/target-utils/usr .`\
    `tar -cf ~/libsincs.tar -C toolchain/target/ bin lib include share`\
    `rm /usr/local/lib/libc.so /usr/local/lib/libpthread.so && (cd /usr/local/lib; ln -s /lib/libc.so.0 libc.so; ln -s /lib/libpthread.so.0 libpthread.so)`

This is already enough for writing and testing hello-world programs.

### Using the Linux configure Mechanism on the Box

-   adapt paths in pkgconfig files (`*.pc`), config files, and library
    linker files (`*.la`)\
    `for i in /usr/local/lib/pkgconfig/*.pc; do sed 's~/home.*uclibc/usr~/usr/local~' $i > $i.tmp; mv $i.tmp $i; done`\
    `for i in /usr/local/bin/*-config; do sed 's~/home.*uclibc/usr~/usr/local~' $i > $i.tmp; mv $i.tmp $i; chmod a+x $i; done`\
    `for i in /usr/local/lib/*.la; do sed 's~/home.*uclibc/usr~/usr/local~' $i > $i.tmp; mv $i.tmp $i; done`
-   download and install the tools `m4`, `autoconf`, `automake`, `bison`,
    and `flex`; sources should be unpacked to `/usr/local/src`\
    `./configure --prefix=/usr/local --disable-nls && make install`

That is enough to configure and build Perl or other complex Linux
packages from source.

### Use the dev-tools Package to Install Compiler and Tools

-   add the dev-tools patch from
    Ticket #2722 "enhancement: NATIVE COMPILER: add target compiler and target tools as m4, automake, ... (closed: wontfix)"
    and toolchain.patch from
    Ticket #2650 "defect: FREETZ_PACKAGE_PYTHON_MOD_CTYPES: can not load shared libs (new)"
    using commands similar to:\
    `for f in $(svn --dry-run patch dev-tools_v4.patch  | grep target | tr -d "'" | cut -d' ' -f4); do mkdir -p $(dirname $f); touch $f; svn add $(dirname $f) 2> /dev/null; rm $f; done`\
    `svn patch dev-tools_v4.patch`\
    `svn patch toolchain.patch`
-   use your download toolchain, select the Dev-Tools package, choose
    Amount of tools -> compiler (fully functional), and select External
    processing -> Dev-Tools
-   create the image and external file. The external file can be uploaded
    through the Freetz web interface. Only if the external file becomes
    too large do you need to split it package-wise with the corresponding
    option, or copy it manually to the box and unpack it into the external
    directory:\
    `tar -xf *.external -C /usr/local`
-   before building, set the environment by sourcing the compiler settings
    from `/usr/local/bin/CFLAGS.sh`:\
    `. /usr/local/bin/CFLAGS.sh`


