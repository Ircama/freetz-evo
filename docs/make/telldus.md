# telldusd (Tellstick daemon)
  - Homepage: [https://telldus.com/](https://telldus.com/)
  - Changelog: [https://github.com/telldus/telldus/releases](https://github.com/telldus/telldus/releases)
  - Repository: [https://github.com/telldus/telldus](https://github.com/telldus/telldus)
  - Package: [master/make/pkgs/telldus/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/telldus/)
  - Steward: Ircama

`telldusd` is the daemon of `telldus-core`, the open source driver of the
Tellstick 433 MHz transmitter/receiver. It owns the USB stick (Tellstick Classic
or Duo, driven through `libftdi`) and serves the client library over the Unix
socket `TelldusClient`, so Domoticz — through the [`libtelldus-core`](../libs/telldus-core.md)
of the [`domoticz`](domoticz.md) package — and the `tdtool` command line client
shipped here can send and receive 433 MHz codes. A Tellstick Duo can also
receive, which is what makes remote controls and sensors of that frequency
usable.

The package builds `service/telldusd` and `tdtool` from the same source archive
as the library package (`make/libs/telldus-core`, which documents the shared
layout and the patches), and installs the daemon, the web page, the init script
and the configuration defaults.

## Configuration

The daemon configuration is the upstream libconfuse format (`user`, `group`,
`device { ... }` sections). Upstream hardcodes two paths that do not work on a
FRITZ!Box — `/etc/tellstick.conf` is read only in the image and `/var/state`
does not exist — so the package patches both into `/mod/etc/conf`, the writable
directory the freetz configuration framework saves to flash:

| File | Content |
|---|---|
| `/etc/tellstick.conf` | default shipped in the image, copied once to the runtime path by the init script |
| `/mod/etc/conf/tellstick.conf` | controller and device list, edited from the web interface (`/cgi-bin/conf/telldus`) or by `tdtool` |
| `/mod/etc/conf/tellstick-state.conf` | state of the devices learned at run time |

The `user` and `group` lines are mandatory: after starting as root, `telldusd`
switches to them and exits when they do not exist. The upstream default,
`plugdev`, does not exist on a FRITZ!Box; the shipped configuration uses `root`.

Four variables are exported by `/mod/etc/default.telldus/telldus.cfg` and shown
on the configuration page (the name prefix is the modconf package name, the rest
is the HTML field name):

| Variable | Field | Meaning |
|---|---|---|
| `TELLDUS_ENABLED` | `enabled` | start the daemon at boot |
| `TELLDUS_DEBUG` | `debug` | add `--debug` to the daemon command line |
| `TELLDUS_EXTRA_ARGS` | `extra_args` | any further `telldusd` option |
| `TELLDUS_DEVICES` | `devices` | the device list as text; the save hook checks the `user`/`group` lines and writes it to `/mod/etc/conf/tellstick.conf` |

## Web interface and build notes

* the page at `http://fritz.box:81/cgi-bin/conf/telldus` holds the start type,
  a text area for the device configuration, the debug switch and extra command
  line options; saving validates the `user`/`group` lines and writes the file
  the daemon reads;
* `/etc/init.d/rc.telldus` starts the daemon with `--nodaemon`, so
  `start-stop-daemon` owns `/var/run/telldusd.pid` and the log ends up in
  `/tmp/rc.telldus.log`;
* `tdtool --list` is the quickest check that the daemon and the stick work.

Build notes: the sources refuse to configure without
`-DFORCE_COMPILE_FROM_TRUNK=TRUE`, they ask for
`cmake_minimum_required(2.6.0)` (CMake 4 needs
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`), and `service/CMakeLists.txt` calls
`PKG_SEARCH_MODULE()`, a macro that current CMake no longer provides: it is
replaced by `FIND_PATH`, with the `libftdi` and `libconfuse` paths passed in
explicitly. `libftdi` 0.20 of this tree matches the 0.x API the source uses.

The 2013-vintage C++ also needs repairs that a patch cannot express, because
the files are stored with CRLF line endings: five sources use `close()`,
`read()` or `va_list` without including `<unistd.h>`/`<stdarg.h>`,
`SettingsConfuse.cpp` compares a pointer against `0`, and the initialiser in
`ProtocolX10.cpp` narrows `169` to `char` (an error since C++11, silenced with
`-Wno-narrowing`). All of them are applied with `$(SED)` in
`$(PKG)_PATCH_POST_CMDS`.

