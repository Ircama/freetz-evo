# Bftpd 6.6
  - Homepage: [https://bftpd.sourceforge.net/](https://bftpd.sourceforge.net/)
  - Manpage: [https://bftpd.sourceforge.net/documents.html](https://bftpd.sourceforge.net/documents.html)
  - Changelog: [https://bftpd.sourceforge.net/downloads/CHANGELOG](https://bftpd.sourceforge.net/downloads/CHANGELOG)
  - Repository: [https://sourceforge.net/projects/bftpd/](https://sourceforge.net/projects/bftpd/)
  - Package: [master/make/pkgs/bftpd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/bftpd/)
  - Steward: [@fda77](https://github.com/fda77)

> "The bftpd program is a small, easy-to-configure FTP server. It
> strives to be fast, secure and quick to install/configure."
> [http://bftpd.sourceforge.net/](http://bftpd.sourceforge.net/)

Bftpd is a small FTP server. To protect access to the FTP server with a
password, proceed as follows:

-   Disable anonymous access on the Freetz configuration page.
-   In a shell (serial console, telnet, or dropbear), change the password
    for the user ftp:

    ``` 
    passwd ftp
    modsave
    ```

Access to the FTP server is now possible only as user ftp with the
assigned password.

### Set Up Additional Users

 * Attention: the AVM daemon `ctlmgr` overwrites `/etc/passwd` when
changes are made in the web interface and deletes the created users. In
addition, Freetz user management has been revised, so new users can now
be created with `adduser username -h /var/media/ftp/uStor01`. This change
must then be made persistent with `modusers save; modsave flash`.

Additional users with freely selectable home directories can be set up
through a small change in `debug.cfg` or with *crond*.

On this page, the lines with user and password required for
`/var/tmp/passwd` can be generated:

```
http://home.flash.net/cgi-bin/pw.pl
```

Alternatively, this can also be done with the Unix/Linux command
`htpasswd`.

The syntax then looks like this:

```
echo "user1:pass1:1000:1:ftp user:/var/media/ftp:/bin/sh" >> /var/tmp/passwd
echo "user2:pass2:1000:1:ftp user:/var/media/ftp:/bin/sh" >> /var/tmp/passwd
echo "user3:pass3:1000:1:ftp user:/var/media/ftp/uStor01/share:/bin/sh" >> /var/tmp/passwd
```

Here, user and pass must be replaced by the previously generated users
and passwords. Like the path specifications, these are of course only
examples. Note the path specification to the USB stick in the third
example. The path must of course exist at login time, otherwise there
will be an error.

*Note:*

-   The password should not be stored in `/etc/passwd`, but in
    `/etc/shadow`. This works on the FritzBox just like on any common
    Linux distribution and is documented in many places on the internet.
-   The individual users receive consecutive user IDs, not all users the
    same ID as shown here (1000). As group ID, 1 (= group "users") can
    and should be used instead of 0 (= group "root").

The AVM FTP is no longer needed now. The filesystem should be set to read
and write without passwords. bftpd should be started with the options
"start automatically" and "not anonymous".

### Modify Existing (Persistent) Users

Addition by [Alexander Kriegisch
(kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)
from 2007-10-13:

How to create and delete persistent users in DS-Mod up to version
ds26-15.2 is explained in the
[How-Tos](../help/howtos/security/user_management.html). Damit
This already gives automatically created users and passwords after the
box boots. The password is entered directly at the console; no external
page is needed to calculate it.

The remaining point is that a user's home directory and UID (unique
numeric user ID) are automatically assigned by DS-Mod each time the box
restarts, because until now they are not stored persistently (this will
also change with 15.3). How to automatically adapt existing user data
accordingly is described
[dort](http://www.ip-phone-forum.de/showthread.php?p=958801#post958801)
there in the forum.

