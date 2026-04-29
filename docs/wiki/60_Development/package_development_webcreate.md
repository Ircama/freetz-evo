# Creating a GUI for Packages in Freetz

### Motivation

A major factor in Freetz's success is that packages can be configured
through a GUI. This article explains the structure and procedure for
creating such a GUI. As a basis and reference point, we assume a virtual
package named `hugo`.

### Basics

Before thinking about the GUI, a few basic things need to be said about
how packages work in Freetz. For basic information, see
[Daniel's documentation](http://www.ip-phone-forum.de/showthread.php?t=90425).
Only a short summary is repeated here; I hope the almost verbatim copying
from Daniel's thread is allowed.

### Custom Packages

A package has the following requirements:

-   rc script:
    `etc/init.d/rc.<paketname> [start|stop|load|unload|restart|status]`

If configurable:

-   Default configuration: `etc/default.<paketname>/<paketname>.cfg`
-   Optional: CGI script for the web interface:
    `usr/lib/cgi-bin/<paketname>.cgi`
-   Optional: extra CGI scripts in `usr/lib/cgi-bin/<paketname>/`

Other default files should also be placed in the directory
`etc/default.<paketname>/`.

-   `/mod/etc/init.d/rc.<paketname>`
-   `/mod/etc/default.<paketname>/*`
-   `/mod/usr/lib/cgi-bin/<paketname>.cgi`
-   `/mod/usr/lib/cgi-bin/<paketname>/*`

are always valid, if included in the package, and are realized through
symlinks for static packages. Binaries should go into `bin`, `sbin`,
`usr/bin`, or `usr/sbin` so they can be called from both static and
dynamic packages. The `PATH` variable also contains `/mod/bin`,
`/mod/sbin`, `/mod/usr/bin`, and `/mod/usr/sbin`. Libraries work for both
static and dynamic packages in `lib`; with `LD_LIBRARY_PATH=/mod/lib`, the
library is searched in `/lib` and `/mod/lib`.

If a package daemon needs a configuration file specific to that daemon,
for example `hugo.conf`, it is usually generated in the rc script before
starting the daemon. I chose the following convention, though it is not
mandatory; it is explained using `bftpd.conf` as an example:

1.  Search for script `/tmp/flash/hugo_conf`, which outputs `hugo.conf`.
    If it exists, go to step 3.
2.  Run script `/etc/default.hugo/hugo_conf`; as in step 1, its output is
    `hugo.conf`, usually this is the case.
3.  If `/tmp/flash/hugo.conf.extra` exists, append it to the `hugo.conf`
    generated in step 1 or 2.

This should leave all fine-tuning possibilities open. Step 3 does not
always make sense, so it is optional. It would be nice if everyone
creating a package followed the conventions. The script `hugo_conf` must
always be called with exported variables from `/mod/etc/conf/hugo.cfg`.
This way, `hugo.conf` is created individually depending on the package
configuration.

### Configuration

Each package has a configuration file
`/mod/etc/conf/<paketname>.cfg`, structured as follows:

```
  export <PAKETNAME>_OPTION1='bla'
  export <PAKETNAME>_OPTION2='blub'
  ...
```

It contains all options that can also be set through the web interface and
uses shell syntax. The current configuration can therefore be loaded with:

```
  . /mod/etc/conf/<paketname>.cfg
```

The default settings are stored in
`/mod/etc/default.<paketname>/<paketname>.cfg`. When saving, only the
variables that differ from the defaults are transferred into
`/tmp/flash/<paketname>.diff` and stored in TFFS together with the whole
`/tmp/flash/` directory. The base configuration has the package name
`mod`. The commands for this are:

```
      modconf load <paketname>
    # -> creates /mod/etc/conf/<paketname>.cfg from the defaults and <paketname>.diff


      modconf save <paketname>
    # -> creates <paketname>.diff from the defaults and /mod/etc/conf/<paketname>.cfg

      modsave
    # -> among other things, calls 'modconf save' for all packages and saves /tmp/flash to TFFS

      modsave flash
    # -> saves only /tmp/flash to TFFS
```

This is how to permanently disable the web interface, using variable
`MOD_HTTPD` in the base configuration `mod`:

```
    vi /mod/etc/conf/mod.cfg  # -> replace MOD_HTTPD='yes' with MOD_HTTPD='no'
    modconf save mod  # mod.diff is now up to date
    modsave flash  # mod.diff is now in TFFS

  # oder

    vi /mod/etc/conf/mod.cfg  # -> replace MOD_HTTPD='yes' with MOD_HTTPD='no'
    modsave  # recreates all diff files and saves them to TFFS
```

That much for illustration. The following is more convenient:

```
  modconf set mod MOD_HTTPD=no
  modconf save mod
  modsave flash

  # bzw.

  modconf set mod MOD_HTTPD=no
  modsave
```

### How Does This Work with the GUI?

The previous section described which files exist and how variable values
can be changed directly from the shell. Freetz GUIs are based on the
concept of
[Proccgi](http://www.fpx.de/fp/Software/ProcCGI.html)
by Frank Pilhofer. They use environment variables that follow the pattern
`<Paketname>_<Variablenname>` as described above. In the HTML pages of
the GUI, input fields are given the tag `name="<Variablenname>"`. These
fields then correspond to the variables. All GUI pages are embedded in a
Freetz wrapper form whose `Apply` button reads these variables and assigns
them to the environment variables.

### An Example

I hope a small example makes this clearer. As already mentioned, our
"package" is named `hugo`. First, create the `default` directory and the
`hugo.cfg` file.

```
    mkdir /mod/etc/default.hugo
    touch /mod/etc/default.hugo/hugo.cfg
```

In the package's `default` directory, `/etc/default.hugo/hugo.cfg`, the
used variables are defined with `export` and at the same time assigned a
default value. Later, when `Default` is clicked in the web interface, the
values defined there are taken over by the GUI. Such a file would look
roughly like this:

```
    export HUGO_ACTION='ACCEPT'
    export HUGO_CHAIN='INPUT'
    export HUGO_DESTINATION='anywhere'
    export HUGO_ENABLED='no'
```

This defines the variables `ACTION`, `CHAIN`, `DESTINATION`, `ENABLED`,
and so on. These variable names are assigned in the GUI, a CGI file, by
input or JavaScript.

The corresponding section in the code:

```
    <p>DESTINATION: <input type="text" name="destination" value="$(html "$HUGO_DESTINATION")"></p>
```

This also shows that the CGI file uses shell evaluation to use the value
of `DESTINATION` as the preset value in the HTML code.

When `Apply` is pressed, these variables are compared with the default
variables and, if they differ, are saved directly to flash in a way that
survives resets.

If `Blabla` is entered in the field, `Apply` creates the file
`/var/tmp/flash/hugo.diff` with this content:

```
    export HUGO_DESTINATION='Blabla'
```

This is also saved immediately with `modsave`. The current file
`/mod/etc/conf/hugo.cfg` is also created by merging the default values and
the changed values in the diff file; it assigns the current value to each
variable. Incidentally, all of this is done by the CGI
`/usr/mww/cgi-bin/save.cgi`, which is called when the form is submitted.

Once the `hugo.cfg` file in the `default` directory is complete, copy it
to `/mod/etc/conf`:

```
    modconf load hugo
```

Now comes GUI programming. Create `hugo.cgi` in
`/mod/usr/lib/cgi-bin/`; it should look roughly like this:

```
    #!/bin/sh

    PATH=/bin:/usr/bin:/sbin:/usr/sbin
    . /usr/lib/libmodcgi.sh

    # sets auto_chk or man_chk to ' checked', depending on HUGO_ENABLED
    check "$HUGO_ENABLED" yes:auto "*":man

    sec_begin 'Activation'
    cat << EOF
    <div style="float: right;"><font size="1">Version 1.0.3</font></div>
    <p>
    <input id="e1" type="radio" name="enabled" value="yes" $auto_chk><label for="e1"> Active</label>
    <input id="e2" type="radio" name="enabled" value="no" $man_chk><label for="e2"> Inactive</label>
    </p>
    EOF
    sec_end

    sec_begin 'hugo heading'
    cat << EOF
    ...
    <p>DESTINATION: <input type="text" name="destination" value="$(html "$HUGO_DESTINATION")"></p>
    ...
    EOF
    sec_end
```

If an additional file should be stored permanently in flash, register it
with `modreg file` and create a file named `hugo_file.def` in
`/mod/etc/default.hugo`. Its content must look like this:

```
    CAPTION='Heading'
    DESCRIPTION='Description of this file. Blah blah blah...'
    CONFIG_FILE='/tmp/flash/hugo_file'
    CONFIG_SAVE='modsave flash;'
    CONFIG_TYPE='text'
```

If the file to be edited must first be generated, the required command can
be specified in `CONFIG_PREPARE`.

The daemon that performs our work is called `rc.hugo` and is created
under `/mod/etc/init.d`. The first lines must look like this:

```
    #!/bin/sh

    DAEMON=hugo

    # Reads package configuration and defines some helper functions
    . /etc/init.d/modlibrc

    start() {
             # PROCESSING GOES HERE
             echo "Starting hugo..."
    }

    stop() {
             # PROCESSING GOES HERE
             echo "Stopping hugo..."
    }

    case "$1" in
            start)
                    start
                    ;;
            stop)
                    stop
                    ;;
            restart)
                    stop
                    start
                    ;;
            status)
                    if [ -z "$(pidof "$DAEMON")" ]; then
                            echo 'stopped'
                    else
                            echo 'running'
                    fi
                    ;;
         ""|load)
                    # Register CGI
                    modreg cgi $DAEMON Label
                    # Register file (stored permanently in flash)
                    # modreg file <pkg> <id> <title> <sec-level>  <desc-file (without path and .def extension)>
                    modreg file 'hugo' 'config' 'HUGO: File' 0 "hugo_file"

                    if [ "$HUGO_ENABLED" != "yes" ]; then
                            echo "$DAEMON is disabled" 1>&2
                            exit 1
                    else
                            start
                    fi
                    ;;

                    ;;
            unload)
                    stop
                    modunreg file 'hugo'
                    modunreg cgi 'hugo'
                    ;;
            *)
                    echo "Usage: $0 [start|stop|restart|status]" 1>&2
                    exit 1
                    ;;
    esac

    exit 0
```

Now clear the cache and add the menu item `hugo` to the web menu.

```
    rm /var/mod/var/cache/menu/packages
    modreg cgi hugo hugo
```

**TIP:** When developing a CGI, store the work on a connected USB stick
and copy the corresponding files into Freetz RAM or create symlinks. Here
is an example of a small script that temporarily copies the files into
RAM.

```
    #!/bin/sh
    mkdir /mod/etc/default.hugo
    cp hugo.cfg /mod/etc/default.hugo
    modconf load hugo
    cd /mod/usr/lib/cgi-bin
    ln -s /var/media/ftp/uStor01/hugo.cgi hugo.cgi
    cd /mod/etc/init.d
    ln -s /var/media/ftp/uStor01/rc.hugo rc.hugo
    modreg cgi hugo hugo
    cd -
```


