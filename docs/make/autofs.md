# AutoFS 5.0.5/5.1.9
  - Homepage: [https://docs.kernel.org/filesystems/autofs.html](https://docs.kernel.org/filesystems/autofs.html)
  - Manpage: [https://github.com/torvalds/linux/blob/master/Documentation/filesystems/autofs-mount-control.rst](https://github.com/torvalds/linux/blob/master/Documentation/filesystems/autofs-mount-control.rst)
  - Changelog: [https://mirrors.edge.kernel.org/pub/linux/daemons/autofs/v5/](https://mirrors.edge.kernel.org/pub/linux/daemons/autofs/v5/)
  - Repository: [https://github.com/torvalds/linux/tree/master/fs/autofs](https://github.com/torvalds/linux/tree/master/fs/autofs)
  - Package: [master/make/pkgs/autofs/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/autofs/)
  - Steward: [@fda77](https://github.com/fda77)

This package can mount various filesystems under /var/media/autofs.

The purpose is that mountpoints are mounted only when they are accessed.
After a timeout without access, they are unmounted again. This works with
all filesystems and is especially practical for network shares (NFS,
CIFS, DAVFS, etc.), because the server to be accessed does not need to be
reachable when the Freetz package that mounts it starts, but only when it
is accessed.

### Optional Invocation Parameters

For troubleshooting, the parameter `-v`, and optionally also `-d`, is
recommended. The messages are output via [syslogd-cgi](syslogd.md).



### Example auto.conf Configurations

### NFS

For NFS, only the nfs.ko module is required.

```
NFS-SHARE -rw,soft,intr,rsize=8192,wsize=8192         SERVER:/SHARE
```

### Samba

For this, the [cifsmount](cifsmount.md) package is required, but not its
web interface.

```
SMB-SHARE -fstype=cifs,user=USER,pass=PASS,ro         ://SERVER/SHARE
```

### WebDAV

For WebDAV, the [davfs2](davfs2.html) package is required, without its
web interface.

```
DAV-SHARE -fstype=davfs     :https://SERVER
```

Additionally, these two files are needed:

/tmp/flash/autofs/davfs2.conf

```
ask_auth 0
#if required:
#if_match_bug 1
```

/tmp/flash/autofs/davfs2.secrets (file permissions 600!)

```
https://SERVER USERNAME    PASSWORT
```

### CurlFtpFS

The CurlFtpFS package is required, without its web interface.

```
FTP-SHARE -fstype=fuse,allow_other       :curlftpfs\#SERVER
```

### SSHfs

The OpenSSH and SSHfs-FUSE packages are required.

```
SSH-SHARE -fstype=fuse,rw,allow_other             :sshfs#USER@SERVER:/
```

In addition, the server must be known in known_hosts, and the private key
must be stored in id_rsa or id_dsa. These files can be edited with the
SSH/[authorized_keys](authorized-keys.md) package.

