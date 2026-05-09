# Apache2 2.4.67 (binary only)
  - Homepage: [https://httpd.apache.org/](https://httpd.apache.org/)
  - Manpage: [https://httpd.apache.org/docs/2.4/](https://httpd.apache.org/docs/2.4/)
  - Changelog: [https://downloads.apache.org/httpd/CHANGES_2.4](https://downloads.apache.org/httpd/CHANGES_2.4)
  - Repository: [https://github.com/apache/httpd](https://github.com/apache/httpd)
  - Package: [master/make/pkgs/apache2/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/apache2/)
  - Steward: [@fda77](https://github.com/fda77)

*This package makes it possible to build the Apache web server either on
its own or with an additional PHP CGI binary.*

Apache can be found under Testing, PHP under Standard packages.

The package contains the minimal directory structure for Apache + PHP.
The configuration files probably still need some adjustments to the
respective needs before everything can then be copied either manually to
a USB device connected to the box (USB stick, hard disk) or into the
`root` directory for integration into the firmware image.

PHP can also be built without Apache; the CGI binary (`sapi/cgi/php`) can
then be found under packages/php-x.y.z (php-cgi). Anyone who needs the
CLI binary (`sapi/cli/php`), however, unfortunately has to obtain it
separately.

Both packages, Apache as well as PHP, are dynamically linked against the
required libraries by default. Anyone who prefers static binaries can
adjust this with the corresponding settings.

If special features are needed, such as SSL for Apache or XML handling in
PHP, the Makefiles must be adjusted accordingly. Corresponding tips and
tricks can be found in the
[Forum](http://www.ip-phone-forum.de/showthread.php?t=127089).

After the build, the Apache package is located in *packages/apache-x.y.z,*
and the config for PHP can also be found there. The PHP binary is
automatically packed into the firmware image; this is not recommended due
to its size. The following procedure is better:

1.  Create a Freetz image without Apache and PHP and flash it to the box.
2.  Select Apache and possibly PHP as [statically linked] binaries and
    run make again.
3.  Put the binaries from *packages/apache-x.y.z* and *packages/php-x.y.z*
    onto an external stick; php-cgi should be placed in Apache's cgi-bin
    folder.
4.  Adjust apache.conf or httpd.conf in the Apache binary. It may be
    necessary to create two symlinks; this can be solved like this, for
    example:

```
  ln -s /var/media/ftp/uStor01/apache/logs /var/logs
```

After that, the Apache commands can be used directly, for example
apachectl start|stop|restart:

```
/var/media/ftp/uStor01/apache/bin/apachectl start
```

**If no self-created binary is used, Apache should (must) be started with
the following command:**

```
httpd-2.2.4/bin/apachectl -f /path/to/Apache/Config/httpd.conf -k start
```

-   If the website is not directly reachable, check under apache/logs to
    see which error messages are output there.
-   If Apache cannot be started at all, run chmod -R 777
    /var/media/ftp/uStor01/apache; possibly chmod -R +x
    /var/media/ftp/uStor01/apache is sufficient.
-   Important: for PHP to work, the following lines must be inserted into
    the Apache configuration:

```
Action       php-script /cgi-bin/php-cgi
AddHandler      php-script .php
```

For CGIs, the following line must be added/uncommented:

```
AddHandler    cgi-script .cgi
```

A ready-made Apache2 binary can also be used with the PHP binary
described above.

If, for example, mod_proxy or even mod_proxy_html is needed, I recommend
the ready-made binary from this
[Thread](http://www.ip-phone-forum.de/showthread.php?t=103110&p=1730858&viewfull=1#post1730858).

### apache.conf

The user must be changed to an existing user; the root user is possible
only with special binaries.

Currently (as of July 2011), the following can be used:

```
User boxusr80
Group root
```

If .htaccess files should be used, AllowOverride must be adjusted
accordingly for the relevant directory; "AllowOverride All" can also be
used.

Here is a corresponding config for a directory; this allows access for
[everyone]:

```
<Directory "/var/media/ftp/uStor01/apache/htdocs">
Options All
AllowOverride    All
Order allow,deny
Allowfrom all
</Directory>

<Directory "/var/media/ftp/uStor01/apache/cgi-bin">
AllowOverride    None
Options ExecCGI
Order allow,deny
Allow from all</Directory>
```

### Password Protection with .htaccess

> If a directory should be protected from unauthorized access using
> *.htaccess*, the following can be added:

```
AuthType
Basic AuthUserFile    /path/to/.ht.password !AuthName    "The website requires credentials" require valid-user
```

> **Important**: the Apache folder contains htpasswd, which can be used
> to create the password file.

```
htpasswd -c/path/to/.ht.password username
```

(This creates a new password file or [overwrites] the existing one with
the specified username.)

To add users to the password file, use the following:

```
 htpasswd/path/to/.ht.password username
```

It is generally recommended to prefix data that should be protected with
.ht; this prevents the user from seeing the file.

### Apache as a Proxy

A good use case for Apache is to use it as a proxy.

This can look as follows: only port 80 is exposed externally. If the user
enters, for example, freetz.meinedomain.at, they reach the Freetz
interface; with fritzbox.meinedomain.at they reach the AVM interface, and
so on.

The advantage is that only one port has to be exposed externally, and the
individual pages can also be protected with a password. For example, the
Fritzbox can no longer be reset if a password has to be entered first.

**Implementation:** This requires Apache with the Proxy module. For this,
I use the
[binary](http://www.ip-phone-forum.de/showthread.php?t=103110&p=1737217&viewfull=1#post1737217)
created by MaxMuster.

Setup is performed as described above. For each additional website that
should be displayed, a VirtualHost must be created. Here is an example
configuration to display the Freetz interface via freetz.meinedomain.at:

```
<VirtualHost *:80>
ProxyPreserveHost On
ProxyPass / http://localhost:81/
ProxyPassReverse / http://localhost:81/
ServerName freetz.meinedomain.at
    <Proxy *>
        Order Deny,Allow
        Allow from all
    </Proxy>
    <Location />
        Require valid-user
        AuthType basic
        AuthName "Passwortgeschuetzt - Login"
        AuthUserFile /path/to/file/.htpasswd
    </Location>
</VirtualHost>
```

The Location element causes the user to have to log in before the page is
built.

### Geoblocking
Certain countries can be blocked through an `.htaccess` file; replace
`XX` accordingly:
```
<IfModule mod_geoip.c>
    GeoIPEnable On
#   SetEnvIf GEOIP_COUNTRY_CODE XX AllowCountry
#   Require env AllowCountry
    SetEnvIf GEOIP_COUNTRY_CODE XX BlockCountry
    <RequireAll>
        Require all granted
        Require not env BlockCountry
    </RequireAll>
</IfModule>
```

### Miscellaneous

If someone gets the idea of running a CMS on the Fritzbox, I recommend
[phpSqliteCms](http://phpsqlitecms.net/). It is a very smart and fast CMS
that runs on the box without problems; only image compression should not
be used. Other CMSs such as Joomla!, Kajona, or even Drupal should be
forgotten because of the low system performance of the
[FritzBox](/search/opensearch?q=wiki%3AFritzBox), unless page load times
of 1-3 minutes are acceptable; for that, php.ini must be adjusted.

### Further Links

-   [Forumsdiskussion](http://www.ip-phone-forum.de/showthread.php?t=127089)
    with tips and tricks about this package
-   [Homepage](http://httpd.apache.org/) of the Apache
    Webservers
-   [Wikipedia
    article](http://de.wikipedia.org/wiki/Apache_HTTP_Server)
    about the Apache web server
-   [Homepage](http://www.apache.org/) of the Apache
    Software Foundation
-   [Wikipedia
    article](http://de.wikipedia.org/wiki/Apache_Software_Foundation)
    about the Apache Software Foundation
-   [Apache Wiki](http://wiki.apache.org/general/)
-   [PHP Homepage](http://de.php.net)
-   [Wikipedia
    article](http://de.wikipedia.org/wiki/Php) about PHP
-   [Apache 1.3.37 and PHP 5.2.0 CGI on the
    FritzBox](http://www.xobztirf.de/selfsite.php?aktion=Apache%20und%20PHP)

