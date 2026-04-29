# shellinabox 2.21
  - Homepage: [https://code.google.com/archive/p/shellinabox/](https://code.google.com/archive/p/shellinabox/)
  - Changelog: [https://github.com/shellinabox/shellinabox/releases](https://github.com/shellinabox/shellinabox/releases)
  - Repository: [https://github.com/shellinabox/shellinabox](https://github.com/shellinabox/shellinabox)
  - Package: [master/make/pkgs/shellinabox/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/shellinabox/)
  - Steward: [@fda77](https://github.com/fda77)

### Notes (2024-02-05 - tested with FritzBox firmware 154.07.57 and Shell-In-A-Box v2.21)
Internally, Shell-In-A-Box uses `/bin/login` by default, and that cannot handle passwords stored in `/etc/shadow`.
As a result, login inevitably fails.

There are two possible solutions for the problem:<br>
1) Copy or move passwords from `/etc/shadow` to `/etc/passwd`.<br>
    (This mainly affects the root user's password.)
    This can be done in an SSH session if you know vi or another text editor.
    To make it permanent, do not forget to run `modsave flash` afterwards.
    In my opinion, however, this is not very nice; when a new SSH password is set, for example via `/usr/bin/passwd`, the password moves back to `/etc/shadow`.<br>
	Therefore I prefer the second solution:<br>
2) Establish an SSH session instead of the LOGIN session.<br>
   The second solution requires a running SSH daemon, for example dropbear, on the box, but who does not have that? ;-)
   Then Shell-In-A-Box must be made to use the *SSH* service instead of the "normal" *LOGIN* service.
   To do this, enter the following under "Service:" on the configuration page of the Shell-In-A-Box package in the Freetz WebUI:<br>
     `/:SSH:<hostname|ip>[:<sshport>]`<br>
     For an SSH daemon that should be reached locally on the box, `localhost` can be entered as *hostname*.
     If the SSH daemon listens on the standard port `22`, the optional *sshport* value can also be omitted.
     For a dropbear package that runs on the box, listens on all interfaces, and whose port is set to `2222`, for example,
     the entry would therefore look like this:<br>
     `/:SSH:localhost:2222`<br>

Incidentally, the Shell-In-A-Box service could also be used to access SSH on other internal computers; according to the documentation, several services separated by spaces can also be defined and active at the same time.
The Shell-In-A-Box documentation explains what else is possible, although it currently does not mention the possibility of specifying the SSH port, even though a patch for this has been integrated since 2018.
If several services are active, a right-click on the Shell-In-A-Box login page (port 4200 by default) should open a menu in which the configured services can be selected. I have not tried this yet.

After switching to the SSH service, login works as well.

