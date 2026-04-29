# Bip 0.9.2 - DEPRECATED
  - Homepage: [https://projects.duckcorp.org/projects/bip](https://projects.duckcorp.org/projects/bip)
  - Manpage: [https://bip.milkypond.org/projects/bip/wiki](https://bip.milkypond.org/projects/bip/wiki)
  - Changelog: [https://projects.duckcorp.org/projects/bip/news](https://projects.duckcorp.org/projects/bip/news)
  - Repository: [https://projects.duckcorp.org/projects/bip/repository](https://projects.duckcorp.org/projects/bip/repository)
  - Package: [master/make/pkgs/bip/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/bip/)
  - Steward: -

The Bip
[IRC](http://de.wikipedia.org/wiki/Internet_Relay_Chat)
proxy is an application which, as the word
*[Proxy](http://de.wikipedia.org/wiki/Proxy_(Rechnernetz))*
already suggests, sits between IRC server and IRC client. It effectively
keeps the permanent connection to the IRC server or servers, can cache
the logs, and can even forward them to a reconnecting client. This makes
it possible, for example, to exchange them between several computers if
you use several computers for chatting.

More information is available on the [BIP
homepage](http://bip.milkypond.org/).

### Selection

[![Menuconfig](../screenshots/212_md.png)](../screenshots/212.png)

If you want to run a Bip proxy on your Fritzbox, it must be selected in
menuconfig when building a Freetz image:

It can be found in **menuconfig** under: **Package selection** =>
**Testing** => Bip 0.8.x


### Configuration

[![Menu in the Fritzbox](../screenshots/213_md.png)](../screenshots/213.png)

In the main menu of the Bip proxy, any port (we chose 2222 in the
example) and the storage location of the log file must then be specified.
You also have to copy the **user.config** from here:

```
###client_side_ssl = false;
### Networks
network {
    name = "freetz";
    server { host = "random.ircd.de"; port = 6667; };
};
### Users
user {
    name = "Mustermann";
    password = "xxxxxxxxxxxxxxxxxxxxxxxx";
    default_nick = "";
    default_user = "Mustermann";
    default_realname = "Mustermann";
    connection {
        name = "freetz";
        network = "freetz";
#       away_nick = "Mustermann-away";
        follow_nick = false;
        ignore_first_nick = false;
        channel {
        name = "#fritzbox";
        };

    };

};
```

and adapt it to your wishes. In practice, only **Mustermann** has to be
changed to your **username**. Under **Networks**, the following entry can
also be used:

```
network {
    name = "freetz";
    server { host = "irc.fu-berlin.de"; port = 6667; };
};
```

**Note:** After **every** change to **user.config** and pressing the
**Apply** button, you have to wait about 5 minutes until the user can log
in to the IRC channel again.

### Further Links

Further explanations of BIP and the settings required in the IRC client
can be found here:
[http://nerderati.com/2010/11/perpetual-irc-the-proxy-edition/](http://nerderati.com/2010/11/perpetual-irc-the-proxy-edition/)

