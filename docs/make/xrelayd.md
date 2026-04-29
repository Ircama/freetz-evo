# Xrelayd 0.2.1pre2 - DEPRECATED
  - Package: [master/make/pkgs/xrelayd/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/xrelayd/)
  - Steward: -

[![Xrelayd Webinterface](../screenshots/203_md.png)](../screenshots/203.png)

*"xrelayd is the successor to matrixtunnel, a lightweight stunnel
replacement. Xrelayd is a basic tcp proxy server which enables you to
encrypt arbitrary protocols without changing ssl unaware deamons and
client software."* [xrelayd thread in the
OpenWRT-Forum](http://forum.openwrt.org/viewtopic.php?id=12338)

Although it is considered the successor to matrixtunnel, this project,
like *matrixtunnel*, has also become somewhat dormant since the end of
2007. *xrelayd* uses a different SSL library than *matrixtunnel* and is
not as compact. Its handling and syntax are similar to *matrixtunnel*.
Unlike *matrixtunnel*, *xrelayd* can also create [self-signed
certificates](http://en.wikipedia.org/wiki/Self-signed_certificate), so
this can be done directly on the box. Such certificates are considered
corrupt by browsers such as Firefox 3, however, because they are "not
trusted" (with "trusted certificates", a
"[Certificate
Authority](http://de.wikipedia.org/wiki/Zertifizierungsstelle)"
such as Thawte or VeriSign vouches for them). AVM appears to use an
xrelayd-like solution for its HTTPS server. The self-signed certificates
newly created for AVM's HTTPS server on every reboot support this
assumption.

Since Freetz trunk Changeset r3571, a WebGUI is also available for this.

### Configuration

1.  Generate the keys on the PC (under Linux):

    ``` 
    openssl genrsa 1024 > host.key
    openssl req -new -x509 -nodes -sha1 -days 365 -key host.key > host.cert
    ```

2.  Paste the keys into the web interface under Settings -> XRelayd:
    Certificate/Private Key.

<!-- -->

3.  Add the desired services. For example:

    ``` 
    0.0.0.0:4433 127.0.0.1:81 Freetz-Webinterface
    ```

4.  Access internally via
    [https://fritz.box:4433](https://fritz.box:4433).
    For external access, a port forward still has to be entered.

### Creating Certificates on the Box

```
xrelayd -f -K 1024 -p host.key -U "CN=localhost" -p host.key -A host.cert
cat host.key > /tmp/flash/.xrelayd/key.pem
cat host.cert > /tmp/flash/.xrelayd/certs.pem
modsave flash
```

