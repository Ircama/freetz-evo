# Maintaining Menu Configuration

One of the first steps for every ***Freetz*** user is selecting the
desired firmware configuration with `make menuconfig`. Menu configuration
is therefore the primary user interface for all non-developers, besides
the Linux shell. Errors and inconsistencies appearing there can, at best,
lead to confusion and questions in the
[IPPF Freetz forum](http://www.ip-phone-forum.de/forumdisplay.php?f=525).
They can also lead to strange console warnings after saving the
configuration, missing or unnecessary firmware components, or in the worst
case to Freetz boxes that no longer boot or get stuck in reboot loops. In
every case, support effort is created. Following the agile mantra "fail
early", the cheapest errors are those noticed as early as possible, or
preferably avoided entirely. Maintaining the menu configuration is an
important quality component of our project.

### Getting Started

Required reading for every developer before changing menu configuration
for the first time should be `tools/kconfig/kconfig-language.txt`. It
explains syntax features and their use. The description comes from the
documentation of the
[Linux-Kernels](http://kernel.org), welchem wir
(and other open-source projects) borrowed this type of menu configuration
and the required tools from.

The most important files and *make* targets involved below are:

-   Config.in
    -   contains the main framework of the menu configuration
    -   is written in the *Kconfig* language
    -   hierarchically includes further menu configuration definitions in
        a tree structure using the `source` directive; these definitions
        also have names such as *Config.in*, *externals.in*, and similar
    -   will in the future, the trunk merge is imminent, be cached as a
        whole with all includes in *Config.in.cache* to reduce load times
        when calling `make menuconfig`
-   *.config*
    -   contains the firmware configuration created by the user and is the
        decisive prerequisite for subsequent builds
    -   is included as a copy in the firmware under */etc/.config* unless
        this is deselected in menu configuration before the build
    -   is one of the primary debugging tools when users report errors
        with a specific configuration
    -   can be edited manually, but should not be
-   *tools/kconfig/mconf*
    -   is the binary called by `make menuconfig` to display and save the
        menu configuration
    -   is built automatically with `make tools` or `make kconfig-host` as
        soon as it is needed
    -   also has a *make* target `menuconfig-single`, which shows the menu
        configuration as a tree structure without subpages; sometimes nice
        when you want to see or edit the overall structure
-   *tools/kconfig/conf*
    -   is the command-line version of *mconf*
    -   has more features
    -   is also built automatically with `make tools` or
        `make kconfig-host` as soon as it is needed
    -   is used by the *make* targets `config`, `oldconfig`,
        `oldnoconfig`, `defconfig`, `allnoconfig`, `allyesconfig`,
        ` randconfig`, `listnewconfig`, `config-clean-deps` und
        `config-clean-deps-keep-busybox` benutzt
    -   shows the following help when called without parameters; this
        works in trunk as of 2011-10-15, not in older stable versions, so
        earliest with *Freetz 1.2*:

        ```
			Usage: tools/kconfig/conf [option] <kconfig-file>
			[option] is _one_ of the following:
			  --listnewconfig         List new options
			  --oldaskconfig          Start a new configuration using a line-oriented program
			  --oldconfig             Update a configuration using a provided .config as base
			  --silentoldconfig       Same as oldconfig, but quietly, additionally update deps
			  --oldnoconfig           Same as silentoldconfig but set new symbols to no
			  --defconfig <file>      New config with default defined in <file>
			  --savedefconfig <file>  Save the minimal current configuration to <file>
			  --allnoconfig           New config where all options are answered with no
			  --allyesconfig          New config where all options are answered with yes
			  --allmodconfig          New config where all options are answered with mod
			  --alldefconfig          New config with all symbols set to default
          --randconfig            New config with random answer to all options
        ```

For now, see ticket #1532, "enhancement: warnings related to new Kconfig
(menuconfig) (closed: fixed)", especially these comments:

-   **Ticket #1532 "comment 10 for ticket #1532": explanation of a
    warning with suggestions for fixing the problem**

    > These *unmet dependencies* are best fixed by whoever happens to
    > encounter them. They are only warnings, but they are important so we
    > can get unclean parts out of the *Config.in* files. That is good for
    > project hygiene. Here is an example:
    >
	> ```
	>	 warning: (FREETZ_PACKAGE_AUTOFS_NFS && FREETZ_PACKAGE_NFSROOT)
	>	     selects FREETZ_MODULE_nfs which has unmet direct dependencies
	>	     (FREETZ_KERNEL_VERSION_2_6_13_1 || FREETZ_KERNEL_VERSION_2_6_28 ||
	>	      FREETZ_KERNEL_VERSION_2_6_32)
    > ```
    >
    > So someone, me, selected NFS-Root. Of course, the NFS kernel module
    > must also be selected for that. But this someone has, for example, a
    > 7270_v1 with kernel 2.6.19.2. The problem is obvious: either this
    > kernel should be added to the dependency list for the NFS module, or
    > all NFS-related things should be disabled for this kernel. Everything
    > else is a contradiction and is flagged by *Kconfig*. What is
    > factually correct in this case, I do not currently know; I have been
    > too far away from development for too long.

<!-- -->

-   **Ticket #1532 "comment 24 for ticket #1532": list of current
    warnings with explanations of causes and possible solutions**
-   **Ticket #1532 "comment 31 for ticket #1532": concrete example of a
    fix checked in by Alexander Kriegisch**

    > Instead of prose, I will just try it schematically:
    > :-)
    >
    > ::: {.code}
    >     FREETZ_PACKAGE_DAVFS2
    >         select FREETZ_REMOVE_WEBDAV if FREETZ_HAS_AVM_WEBDAV
    >
    >     FREETZ_REMOVE_WEBDAV
    >         depends on FREETZ_HAS_AVM_WEBDAV
    >
    >     FREETZ_HAS_AVM_WEBDAV
    >         depends on FREETZ_TYPE_FON_WLAN_7240 || ...
    > :::
    >
    > This looks clean enough to me, even though the `if
    > FREETZ_HAS_AVM_WEBDAV`, I agree with you there, is duplicated in
    > your sense. But it says more precisely what you really want to do;
    > this time the configuration statement can truly be read like prose:
    > select the remove patch if there is anything to remove at all. I
    > think that makes it sufficiently clear and documents once again what
    > is intended. It also avoids the warning after saving the
    > configuration. Without the *if*, the warning would appear.

<!-- -->

-   **Ticket #1532 "comment 54 for ticket #1532": generalized recipe for
    fixing problems with remove patches**

    > I point once again to my comment #31, from which one can basically
    > see very nicely how simply, elegantly, and readably many situations
    > can be fixed:
    >
    > ::: {.code}
    >     FREETZ_PACKAGE_FOO
    >         select FREETZ_REMOVE_MY_FEATURE if FREETZ_HAS_AVM_MY_FEATURE
    >
    >     FREETZ_REMOVE_MY_FEATURE
    >         depends on FREETZ_HAS_AVM_MY_FEATURE
    >
    >     FREETZ_HAS_AVM_MY_FEATURE
    >         depends on FREETZ_TYPE_A || FREETZ_TYPE_B || ...
    > :::
    >
    > **Recipe for remove patches (RP):**
    >
    > -   Secure automatic RP selection with
    >     `if FREETZ_HAS_AVM_MY_FEATURE`
    > -   Make RP visibility depend on
    >     `depends on FREETZ_HAS_AVM_MY_FEATURE`
    > -   Make the feature removable by the RP depend on hardware or
    >     firmware and so on with `depends on FREETZ_TYPE_A`

<!-- -->

-   **Ticket #1532 "comment 55 for ticket #1532": further explanations
    for implementing the recipe**

    > Replying to oliver:
    >
    > > What is the point of removing a dependency that is correct, except
    > > for a few cases?
    >
    > I quickly looked at the first patch after all. It is neither correct
    > to leave the dependency in if it is wrong in even a few cases, nor to
    > remove it without replacement if nonsensical options are then shown
    > in new, wrong cases. What would make sense, although it takes some
    > effort, would be applying my recipe and creating new variables
    > `FREETZ_HAS_AVM_AURA_USB`, `FREETZ_HAS_AVM_PRINTSERV`, and
    > `FREETZ_HAS_AVM_RUNCLOCK`. As far as I am concerned,
    > `FREETZ_HAS_USB_HOST` could automatically select them in cases where
    > there are no contrary findings. But as soon as even one exception is
    > known, a box list must be stored for the respective `FREETZ_HAS_AVM_*`.
    > Remove patches should always depend on `FREETZ_HAS_AVM_*`, never on a
    > cheap substitute that works *almost* always.
    >
    > This is not criticism in the sense of "you should have known that
    > beforehand", because these insights are relatively new and, in my
    > opinion, a blessing of the new *Kconfig*. With my notes, I want to
    > give other developers help for self-help.
    >
    > Addition: something like this is also conceivable:
    >
    > ::: {.code}
    >     FREETZ_HAS_AVM_MY_FEATURE
    >         depends on FREETZ_HAS_USB_HOST && !(FREETZ_TYPE_A || FREETZ_TYPE_B)
    > :::
    >
    > This keeps the box list small by simply stating clearly what is the
    > case. It is again almost readable like prose: "Show AVM feature X if
    > the box has a USB host, except in exception cases A and B."

### Find Syntax Errors in Menu Configuration Files

We see an error like this:

```
	$ make menuconfig

	Config.in.cache:4951: syntax error
	Config.in.cache:4950: unknown option "xconfig"
	Config.in.cache:4951:warning: prompt redefined
	make: *** [menuconfig] Error 1
```

According to the description in changeset r8466, there are two ways to
quickly find the faulty location when `make menuconfig` reports a syntax
error:

1.  In `Config.cache.in`, jump directly to the error line shown on the
    console, line 4950 in the example. From there, search backwards for
    `INCLUDE_BEGIN`; there is the filename containing the faulty menu
    configuration.
2.  Call `make menuconfig-nocache` and read the problematic file,
    *make/davfs2/Config.in*, directly from the console:

    ```
		$ make menuconfig-nocache

		make/davfs2/Config.in:2: syntax error
		make/Config.in:84: missing end statement for this entry
		Config.in:851: missing end statement for this entry
		make/davfs2/Config.in:1: invalid statement
		make/davfs2/Config.in:2: unexpected option "bool"
		make/davfs2/Config.in:3: unexpected option "select"
		make/davfs2/Config.in:4: unexpected option "select"
		make/davfs2/Config.in:5: unexpected option "select"
		make/davfs2/Config.in:6: unexpected option "select"
		make/davfs2/Config.in:7: unexpected option "select"
		make/davfs2/Config.in:8: unexpected option "select"
		make/davfs2/Config.in:9: unexpected option "default"
		make/davfs2/Config.in:10: invalid statement
		make/davfs2/Config.in:11: unknown statement "davfs"
		make/davfs2/Config.in:12: unknown statement "WebDAV"
		make/davfs2/Config.in:13: unknown statement "HTTP"
		make/davfs2/Config.in:14: unknown statement "resources"
		make/Config.in:199: unexpected end statement
		Config.in:862: unexpected end statement
		make: *** [menuconfig-nocache] Error 1
    ```

### Syntax Highlighting for Menu Configuration Files

According to `tools/developer/kconfig.pygments.patch`, I, Alexander
Kriegisch, kriegaex, first built a so-called
[Lexer](http://de.wikipedia.org/wiki/Lexikalischer_Scanner)
for [Pygments](http://pygments.org), see also the
[Pygments documentation](http://pygments.org/docs/lexerdevelopment/),
which makes it possible to provide syntax highlighting for menu
configuration files. *Pygments* is used automatically by
[Trac](http://trac.edgewall.org), also dem System,
the system on which our wiki and repository browser are based, if it is
installed.

However, *Trac* recognizes a file's MIME type only from the extension,
for example `*.py`, `.sh`, `.pl`, `.c`, `.h`, or from information such as
[Shebang](http://de.wikipedia.org/wiki/Shebang)
or *Vi/Emacs* headers. This is a problem for menu configuration files,
because there is no standardized file extension in general, nor in our
project. Our only chance is to keep the proliferation of file names, for
example *Config.in*, *external.in*, *standard-modules.in*,
*external.in.libs*, under control enough that the corresponding files can
be identified with
[regex matching](http://de.wikipedia.org/wiki/Regul%C3%A4rer_Ausdruck).
This is possible today, but *Trac* does not support regex matching out of
the box, so `tools/developer/mime_map_patterns.trac.patch` becomes
necessary. Note: before patch 2 existed, it was necessary in SVN to set
the property `svn:mime-type` manually for each menu configuration file.
Fortunately this is now obsolete, although it would not hurt either.

On our web server, both patches are active together with the required
configuration in `trac.ini`, so menu configuration files from the SVN
repository are automatically syntax-highlighted.

One small tip: how to use syntax highlighting directly in code blocks in
the *Trac* wiki can be seen in this article for menu configuration and
shell code. Either mention the MIME type at the beginning of the code
block with a leading shebang, `text/x-kconfig`, incidentally invented by
us and not a general standard, or use the keyword `kconfig` configured in
`trac.ini`, roughly like this:

```
	{{{
	#!text/x-kconfig
	... MK-Code ...
	}}}
```

Or like this:

```
	{{{
	#!kconfig
	... MK-Code ...
	}}}
```


