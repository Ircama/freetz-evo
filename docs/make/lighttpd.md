# Lighttpd 1.4.82
  - Homepage: [https://www.lighttpd.net/](https://www.lighttpd.net/)
  - Manpage: [https://wiki.lighttpd.net/](https://wiki.lighttpd.net/)
  - Changelog: [https://www.lighttpd.net/releases/](https://www.lighttpd.net/releases/)
  - Repository: [https://git.lighttpd.net/lighttpd/lighttpd1.4.git](https://git.lighttpd.net/lighttpd/lighttpd1.4.git)
  - Package: [master/make/pkgs/lighttpd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/lighttpd/)
  - Steward: [@fda77](https://github.com/fda77)

This package makes it possible to build the lighttpd web server.

### Setup

To use the web server, a directory must be created in which lighttpd can
operate. This must absolutely be created and given the required
permissions.


**Important:** This guide assumes that [USB-root](usbroot.md) is used. If
USB-root is not used, even more attention must be paid to the following
directory structures. In such a case,
`/var/media/ftp/uStor01/rootfs/www` **could** be an analogue for `/www`.


First, a console session with the router must exist; it does not matter
whether Telnet or [SSH](dropbear.md) is used for this.

```
# create web server directory and set 'rwxr-xr-x' permissions
mkdir /www
chmod -R 755 /www
```

The lighttpd settings can now be adjusted and applied in the Freetz
configuration frontend. The required directory structure is then created
inside the web server directory. Documents must be located in the
`/www/websites` directory. Depending on the settings, the server is now
available, for example, at `http://fritz.box:8008`.

### Perl

If Perl scripts should be used with the web server and `chroot` mode
should be used, make sure that the [microperl](microperl.md) package and
its libraries are copied into the lighttpd directory structure.

```
# copy 'microperl' as 'perl' into the web server's '/usr/bin' directory
cp -p /usr/bin/microperl /www/usr/bin/perl

# create a '/lib' directory for the libraries
mkdir /www/lib

# copy the libraries required by 'microperl' into the web server's '/lib' directory
# dependencies can be displayed with 'ldd /usr/bin/microperl'
cp -p /lib/ld-uClibc.so.0 /www/lib
cp -p /lib/libc.so.0 /www/lib
cp -p /lib/libgcc_s.so.1 /www/lib
cp -p /lib/libm.so.0 /www/lib
```

If `*.pl` files should be executed in addition to `*.cgi` files, a line
must also be added to the 'Additional' configuration of lighttpd (found
in the Freetz configuration menu under `Settings` ->
`lighttpd: Additional`):

```
# enable CGI support for *.pl files
cgi.assign += ( ".pl" => "/usr/bin/perl" )
```

Also make sure that all Perl scripts have execute permissions; this can
be done with a simple `chmod 755 FILE.pl`.

### Lua

make menuconfig:

-   *lighttpd > build with LUA support*
-   *lighttpd > lighttpd Modules > include mod_magnet*

Example:

-   put this in *lighttpd > Additional*:

```
server.modules += ( "mod_magnet" )
magnet.attract-physical-path-to = ( server.document-root + "/ip.lua" )
```

-   put this in *ip.lua* in your document root:

```
lighty.header["Content-Type"] = "text/html"
lighty.content = { "Your IP-address is: ", lighty.env["request.remote-ip"] }
return 200
```

-   browse to *http://fritz.box:<configured port>/ip.lua*

### Geoblocking
To block access from certain countries, the lighttpd modules `mod_magnet`
and `mod_maxminddb` are used. This selects the `libmaxminddb` library,
which requires a `GeoLite2-City.mmdb` database (~70 MB) that can be
downloaded from [https://github.com/P3TERX/GeoLite.mmdb/](https://github.com/P3TERX/GeoLite.mmdb/).

Also create a LUA script `geoblock.lua`; adjust `XX` accordingly:
```
if (lighty.r.req_env["GEOIP_COUNTRY_CODE"] == "XX") then return 403 end
return 0
```

Extension of the lighttpd configuration; adjust the paths of the `.lua`
and `.mmdb` files:
```
server.modules += ( "mod_maxminddb" )
maxminddb.activate = "enable"
maxminddb.db = "/var/media/ftp/GeoLite2-City.mmdb"
maxminddb.env = (
 "GEOIP_COUNTRY_CODE"   => "country/iso_code",
 "GEOIP_COUNTRY_NAME"   => "country/names/en",
 "GEOIP_CITY_NAME"      => "city/names/en",
 "GEOIP_CITY_LATITUDE"  => "location/latitude",
 "GEOIP_CITY_LONGITUDE" => "location/longitude",
)

server.modules += ( "mod_magnet" )
magnet.attract-raw-url-to = ( "/var/media/ftp/geoblock.lua" )
```

### Links

-   [The Programming Language
    LUA](http://www.lua.org/)
-   [Lighttpd - Docs:ModMagnet - lighty
    labs](http://redmine.lighttpd.net/wiki/lighttpd/Docs:ModMagnet)
-   [AbsoLUAtion - The powerful combo of Lighttpd +
    Lua](http://redmine.lighttpd.net/wiki/1/AbsoLUAtion)

Advantage over PHP: small, fast, low memory usage, feature rich
programming language.

### Further Links

-   [Wikipedia
    article](http://de.wikipedia.org/wiki/Lighttpd) about
    Lighttpd
-   [Lighttpd Homepage](http://www.lighttpd.net)
-   [Forumsdiskussion](http://www.ip-phone-forum.de/showthread.php?t=185448)
    in IPPF about this package
-   [HowTo](http://www.howtoforge.com/setting-up-webdav-with-lighttpd-debian-etch)
    setting up webdav with lighttpd in Debian Etch
-   [HowTo](http://www.howtoforge.de/howto/wie-man-webdav-mit-lighttpd-auf-debian-etch-konfiguriert)
    (same as above, in German)

