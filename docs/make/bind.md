# BIND 9.11.37/9.20.22
  - Homepage: [https://www.isc.org/bind/](https://www.isc.org/bind/)
  - Manpage: [https://bind9.readthedocs.io/en/](https://bind9.readthedocs.io/en/)
  - Changelog: [https://downloads.isc.org/isc/bind9/cur/9.20/](https://downloads.isc.org/isc/bind9/cur/9.20/)
  - Repository: [https://gitlab.isc.org/isc-projects/bind9/](https://gitlab.isc.org/isc-projects/bind9/)
  - Package: [master/make/pkgs/bind/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/bind/)
  - Steward: [@fda77](https://github.com/fda77)

With [bind](http://isc.org/software/bind) (Berkeley Internet Name
Daemon), a DNS server can be operated for IP and name resolution.



### named.conf

The available options can be taken from the man page or from the many web
pages about BIND.

Minimal *named.conf*:

```
options {
    directory "/var/media/ftp/uFlash/bind";
    listen-on port 53 { any; };
    allow-query { any; };
    notify no;
};

zone "example.org" in {
      type master;
      file "example.org";
};
```

Minimal zone file */var/media/ftp/uFlash/bind/example.org*:

```
$TTL 300
@       IN      SOA     @ example.org. (
                        2011032701      ;serial
                        300             ;refresh
                        300             ;retry
                        300             ;expire
                        300             ;minimum
                        )

        IN      NS      ns.example.org.
*       IN      A       85.214.209.234
```
