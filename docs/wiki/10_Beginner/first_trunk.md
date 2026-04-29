# How Do I Build My First Trunk?

### Description for a Trunk Image Including Samba and VSFTP

These instructions are written for everyone who wants to modify their
FRITZ!Box with a FREETZ trunk, the developer version, for the first time.

### Build a Trunk Image

The procedure for building a trunk image is identical to the steps in the
newbie tutorial up to **check out Freetz sources**. Therefore, this guide
starts at that point. If you are unsure, go through the tutorial again up
to "check out Freetz sources".

The checkout command now looks a little different. Enter the following
command:

```
	git clone https://github.com/Freetz-NG/freetz-ng ~/freetz-ng
```


If this does not start, the network connection may not be working. In that
case, a **ping 192.168.XXX.1** from the console should show whether the
network connection works. The Freetz sources should now be downloaded.
Afterwards, change into the Freetz directory with **cd freetz-trunk** and
enter **make menuconfig**.

[![auschecken von Freetz](../../screenshots/72_md.png)](../../screenshots/72.png)

After this input, you should see the following screen:

[![menuconfig](../../screenshots/73_md.png)](../../screenshots/73.png)

This is again the configuration interface of the Freetz build system.
Select the respective router and desired packages there. For this how-to,
we use the 7270_v2 as an example. First, activate the advanced view on the
first page, **Level of user competence** -> **Advanced**. Then select the
following patches for a Freetz image:\
**Under Firmware language:**

-   Select whether you want to create German or English firmware.
	Warning: the selection must match the existing box.

**Under Other patches:**

-   **FREETZMOUNT**
-   **Automount Filesystems**
    -   **NTFS**

**Under Removal patches:**

-   **Remove ftpd (NEW)**; one FTP program on the box is enough.

[![Patches](../../screenshots/187_md.png)](../../screenshots/187.png)

**Under Packages/Standard packages:**

-   **Samba suite**, a server that allows Windows access to USB media on
	the FRITZ!Box. The check marks for the two Samba sub-items `smbd` and
	`nmbd` must be set.
-   **VSFTP**, FTP server. Do not set any further check marks for its
	sub-items.

[![Patch : SAMB und VSFTP](../../screenshots/186_md.png)](../../screenshots/186.png)

**Under Packages/Web interfaces:**

-   **AVM-firewall**, a web interface for administering the integrated
	firewall that AVM withholds from the user.
-   **spindown-cgi 0.2**
-   **Syslogd CGI 0.2.3**

[![Patche : Web interfaces](../../screenshots/185_md.png)](../../screenshots/185.png)

**Under Web Interface:**

-   **Favicons (none) --->** select a favicon. This is the image displayed
	as a bookmark in the browser.

[![Patch : Advanced options](../../screenshots/188_md.png)](../../screenshots/188.png)

[![Screenshot](../../screenshots/228_md.png)](../../screenshots/228.png)

Further packages and patches, including their descriptions, can be found
on the package page.

After selecting all packages and patches, exit the configuration and enter
**make** on the shell command line. You should now see a screen like this:

[![Run make](../../screenshots/189_md.png)](../../screenshots/189.png)

The build process starts again. The flow is identical to the first image.
The created image is again placed in the **images** subdirectory of the
Freetz directory.

The final message looks like this:

[![make is finished](../../screenshots/190_md.png)](../../screenshots/190.png)



The steps **copy image to the PC** and the flashing process are again
identical to the newbie tutorial.

### Configure Samba

Samba must first be configured. Go to **Packages/Samba**. Set startup type
to **automatic** and assign a NetBIOS name. The check mark at
**Preferred master** is important because it replaces the FRITZ!Box's
standard Samba server.

[![Freetz-WebIF](../../screenshots/192_md.jpg)](../../screenshots/192.jpg)


The rest can be left as is; click **Samba shares**.

[![Freetz-WebIF](../../screenshots/193_md.jpg)](../../screenshots/193.jpg)

Here, as an example, we have created two shares on the USB HDD of the
FRITZ!Box: one for **guest** and the second for **family**. A short
description of the parameters using the first share:

- **/var/media/ftp/uStor01** is the internal path to the hard disk.\
- **/Videos** is the shared directory.\
- **hdd1** is the share name shown in the Windows network environment.
- **1** allows guest access; no username and password required.\
- **0** enables read-write access.\
- **-** reason for the dash: unknown; it must be present, explanation to
	follow.\
- **Videos** comment.

**Example:**

```
	/var/media/ftp/uStor01/Videos hdd1 1 0 - Videos
```

Because we assigned **fritz** as the NetBIOS name, Windows accesses the
share as `fritz\hdd1`. Now start the Samba server under **Services**, and
it should work.


### Configure FTP Shares (Freetz Trunk)

**Warning: this description is based on a trunk image. FTP shares for
Freetz 1.1.x images will be explained later.**

First, a folder structure must be created on the USB disk. Simply format
your USB stick or hard disk as FAT32. NTFS would also work, but is not
described in more detail here. Your disk should then look like this:

[![Screenshot](../../screenshots/81_md.jpg)](../../screenshots/81.jpg)

If that is the case, connect the stick to your FRITZ!Box. In the rest of
this description, we assume a stick. Now, if not already done while
configuring Samba, disable AVM's FTP solutions:

-   fritz.box → Settings → Advanced settings → USB devices →
	USB storage/storage (NAS)
-   Enable USB storage FTP access -> remove check mark
-   Enable USB network storage -> remove check mark

It should now look like this:

[![Screenshot](../../screenshots/82_md.jpg)](../../screenshots/82.jpg)

Now switch to the Freetz interface:
[http://fritz.box:81/](http://fritz.box:81/) und
enter the following under Services -> vsftp:

-   Startup type: Automatic
-   Access: set check marks for **Local users** and **chroot jail**;
	remove all other check marks.
-   Additional configuration options for experts:
    **user_config_dir=/var/media/ftp/uStor01/vsftp_user_conf**
-   Logging: **/var/media/ftp/uStor01/vsftpd.log**; can be enabled but is
	not required.


Apply all entries by pressing **Apply**. It should then look like this:

[![Freetz-WebIF](../../screenshots/194_md.jpg)](../../screenshots/194.jpg)

[![Screenshot](../../screenshots/84_md.jpg)](../../screenshots/84.jpg)

Now turn to the AVM firewall:

-   Go to Packages -> AVM-Firewall and the Forwarding item. The FTP port
	still has to be opened here; see the screenshots.

[![Screenshot](../../screenshots/85_md.jpg)](../../screenshots/85.jpg)

After entering the numbers, see above, simply press **Add** and the result
should look as follows:

[![Screenshot](../../screenshots/86_md.jpg)](../../screenshots/86.jpg)

To finally save this setting, simply set the check mark, the blinking box,
and wait for the box to reboot. After the box has started again, open the
**Services** tab in the Freetz web interface once more and activate the
**telnetd** service. It must be started to configure the FTP users in the
next step. It is not recommended to set this service to automatic; start
it manually when needed.

For now, leave the web interface and move to the FRITZ!Box command line.
For this, Windows users first need
[PuTTY](http://putty.softonic.de/), which must be downloaded and
installed on the PC. This step is needed only for Windows users. Linux
users can start a Telnet session as usual. PuTTY can be downloaded as
freeware here: [Download](http://putty.softonic.de/) and is configured as
follows:

[![Screenshot](../../screenshots/87_md.jpg)](../../screenshots/87.jpg)

After pressing **Open** and entering **login: root** and **password:
freetz**, you should see this screen:

[![Screenshot](../../screenshots/88_md.jpg)](../../screenshots/88.jpg)




### Create Users

The command is structured like this:
`adduser -h '''directory''' '''username'''`

> **Directory**: folder on the stick that should be assigned to the user,
> for example **/var/media/ftp/uStor01/**
> **Username**: name of the user

When creating the user, the password is requested immediately. It must be
entered twice; nothing is shown on screen, not even asterisks. We now want
to create a user **Paul** and a user **Mary**, who should receive FTP
access to the folders **hdd1** for Paul and **hdd2** for Mary; see Samba.
Additionally, a user **Guest** with read-only rights to folder **hdd1** is
created. Enter the following commands in PuTTY; pay attention to upper and
lower case:

```
	/var/mod/root # adduser -h /var/media/ftp/uStor01/hdd1 paul
	adduser: /var/media/ftp/uStor01/hdd1: Operation not permitted
	Changing password for paul
	New password:
	Bad password: too short
	Retype password:
	Password for paul changed by root
```

The message `Operation not permitted` appears when the filesystem is FAT
or NTFS. Now do the same again for Mary and guest:

```
	adduser -h /var/media/ftp/uStor01/hdd2 mary
	adduser -h /var/media/ftp/uStor01/hdd1 gast
```

To change a password, use the command `passwd `**`username`**. You are
again asked twice for the new password. A user can be deleted with
`deluser `**`username`**. In every case, changes must be saved again with
**modsave all**. The file can be displayed with **cat /var/tmp/passwd**.
Displaying and changing is also possible through the Freetz Rudi shell.
This is available only when the security level is set to 0. If everything
went correctly, `passwd` should contain the following:

```
	root:x:0:0:root:/mod/root:/bin/sh
	ftp:x:2:1:FTP account:/home/ftp:/bin/sh
	ftpuser:x:1:1:ftp user:/var/media/ftp:/bin/sh
	paul:x:1000:1000:Linux User,,,:/var/media/ftp/uStor01/hdd1:/bin/sh
	mary:x:1001:1001:Linux User,,,:/var/media/ftp/uStor01/hdd2:/bin/sh
	gast:x:1002:1002:Linux User,,,:/var/media/ftp/uStor01/hdd1:/bin/sh
```

Now log out from the PuTTY console with this command:

```
	exit
```




### Assign Rights for FTP Users

> Whether a new FTP user should receive write rights or read-only access
> is controlled as follows:\
> Each user receives a file with their filename in the folder
> **/var/media/ftp/uStor01/vsftp_user_conf/**, which determines whether
> the user has write rights or not.

File content:

> **write_enable=yes**: user has write rights; see Paul and Mary.\
> **write_enable=no**: user has **no** write rights; see guest.

These user files also make it possible to forbid individual FTP commands
([list](http://en.wikipedia.org/wiki/List_of_FTP_commands)) for users.
Add the following line to the file and remove the commands the user is not
allowed to execute:

```
	cmds_allowed=ABOR,ACCT,ALLO,APPE,AUTH,CDUP,CWD,DELE,EPRT,EPSV,FEAT,HELP,LIST,MDTM,MKD,MODE,NLST,NOOP,OPTS,PASS,PASV,PBSZ,PORT,PROT,PWD,QUIT,REIN,REST,RETR,RMD,RNFR,RNTO,SITE,SMNT,STAT,STOR,STOU,STRU,SYST,TYPE,USER
```

**Example:** Mary may copy files to FTP and create directories, but may
not delete them again. Therefore, the following must be in the file:

```
	cmds_allowed=ABOR,ACCT,ALLO,APPE,AUTH,CDUP,CWD,EPRT,EPSV,FEAT,HELP,LIST,MDTM,MKD,MODE,NLST,NOOP,OPTS,PASS,PASV,PBSZ,PORT,PROT,PWD,QUIT,REIN,REST,RETR,RNFR,RNTO,SITE,SMNT,STAT,STOR,STOU,STRU,SYST,TYPE,USER
```

> **DELE** (Delete file), **RMD** (Remove a directory) were removed from
> the string above.
> \
> \
> If something still does not work, simply restart the router again.




### Build an Image for a Speedport

Unfortunately, Speedports cannot be flashed through the AVM web interface
because of a software lock. Use the Freetz tools `recover-eva` or
`push_firmware`, or GUI programs from the forum such as
[ruKernelTool](http://rukerneltool.rainerullrich.de/index.html). It works
very well and is easy to use.

### Which Speedports Can Be Modified with Freetz?

-   W501V
-   W701V
-   W900V
-   W920V

### Converting a W701V

1. Start Freetz Linux as described above.
2. Work through all steps as described in the [how-to](first_trunk.html),
but select 7170 as box type and set W701V under Alien hardware type.

[![Speedport_Trunk_2](../../screenshots/196_md.png)](../../screenshots/196.png)

[![Speedport_Trunk_3](../../screenshots/197_md.png)](../../screenshots/197.png)

3. Samba and VSFTP are useful only on a W920V (7570), because it has a USB
port. All other steps in the [how-to](first_trunk.html), however, also
apply to a Speedport.

4. The created image should be loadable into the box as a normal firmware
update. If the box refuses the update, which happened with my W701V, the
only remaining way is through
[ruKernelTool](http://rukerneltool.rainerullrich.de/index.html). In that
case, however, all access data and settings are lost. The box effectively
performs a factory reset.

**Result:**

[![Speedport_Trunk_1](../../screenshots/195_md.png)](../../screenshots/195.png)

### Converting a W501V

The W501V can be selected directly as the box type.

### Converting a W920V

Box type: 7570 VDSL\
Alien type: W920V

[![Speedport_Trunk_4](../../screenshots/198_md.png)](../../screenshots/198.png)


