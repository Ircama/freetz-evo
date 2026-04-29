# Shut Down Computers on the Network

With the Freetz packages `wol` and `callmonitor`, it is easy to start a
computer on the network by mobile phone or through the Freetz web
interface. Shutting down a computer behind a FRITZ!Box can be just as
simple. The configuration is not difficult and works for both Linux and
Windows computers.

### Requirements

-   FRITZ!Box with the packages `dropbear`, including the SSH client, and
    `callmonitor`

### Configure the FRITZ!Box

### Generate Keys

-   Log in to the FRITZ!Box, create a directory, and generate keys:
    ```
		mkdir /var/tmp/flash/ssh
		cd /var/tmp/flash/ssh
		dropbearkey -t rsa -f rsakey_box
    ```

-   Extract the public key:
    ```
		dropbearkey -y -f rsakey_box | grep ssh > rsakey_box.pub
    ```

### Configure the FRITZ!Box for a Linux Computer to Shut Down

-   On the FRITZ!Box, create a file such as
    `/var/tmp/flash/ssh/shutdown_linuxrechner.sh` with the following
    content. Some distributions prevent user `root` from logging in by
    default. Change that setting, or preferably replace `root` with a user
    that, for security reasons, only has permission to shut down the
    computer.

```
		ssh -i /var/tmp/flash/ssh/rsakey_box root@<ip_rechner> "shutdown -h now"
```

-   As the final configuration step on the FRITZ!Box, add this line to the
    Callmonitor listeners:

```
		in:request ^<abgangsrufnummer> ^<eingangsrufnummer> HOME=/mod/root && /var/tmp/flash/ssh/shutdown_linuxrechner.sh
```

### Configure the FRITZ!Box for a Windows Computer to Shut Down

-   On the FRITZ!Box, create a file such as
    `/var/tmp/flash/ssh/shutdown_windowsrechner.sh` with the following
    content. Replace `<benutzername>` with the Windows user name:
    ```
		ssh -i /var/tmp/flash/ssh/rsakey_box <benutzername>@<ip_rechner> "shutdown -s"
    ```

-   Add this line to the Callmonitor listeners:

    ```
		in:request ^<abgangsrufnummer> ^<eingangsrufnummer> HOME=/mod/root && /var/tmp/flash/ssh/shutdown_windowsrechner.sh
    ```

### Configure the Linux Computer to Shut Down

-   Copy the public key, the one extracted earlier, from the FRITZ!Box to
    the target computer and authorize it. Replace `root` with
    `/home/<benutzername>` if necessary, and make sure that this user is
    allowed to shut down the computer:
    ```
		cat rsakey_box.pub >> /root/.ssh/authorized_keys
    ```

-   Install and start the OpenSSH server.

### Configure the Windows Computer to Shut Down (Tested on Windows XP)

-   Copy the public key from the FRITZ!Box to the target computer, rename
    it to `authorized_keys`, and place it in
    `c:\\Dokumente und Einstellungen\\benutzername\\.ssh\\`. On the
    author's computer, the folder had to be created in the terminal with
    `mkdir .ssh` because of the leading dot.

-   Install [OpenSSH](http://sshwindows.sourceforge.net/).

-   Adjust the configuration file `c:\\programme\\openssh\\etc\\sshd_config`.
    Correct these values:

    ```
		StrictModes no
		RSAAuthentication yes
		PubkeyAuthentication yes
		AuthorizedKeysFile  .ssh/authorized_keys
	```

The computer can now be shut down by calling the phone number configured
in the Callmonitor listener. It also works through the Freetz web
interface under Extras, Test call.

### Notes

-   The computer to be shut down must be listed in
    `/mod/root/.ssh/known_hosts`. The easiest way to achieve that is to
    connect once from the FRITZ!Box to the computer through SSH.

-   To make sure the created files are not lost after a FRITZ!Box reboot,
    run `modsave flash`.


