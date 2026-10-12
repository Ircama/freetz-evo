# telldus-core: libtelldus-core (libtelldus-core.so) 2.1.1
  - Homepage: [https://telldus.com/](https://telldus.com/)
  - Changelog: [https://github.com/telldus/telldus/releases](https://github.com/telldus/telldus/releases)
  - Repository: [https://github.com/telldus/telldus](https://github.com/telldus/telldus)
  - Library: [master/make/libs/telldus-core/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/telldus-core/)
  - Steward: -

libtelldus-core is the client library of telldus-core, the open source driver of the Tellstick (USB and Duo) 433 MHz transmitter/receiver. Programs using it (e.g. Domoticz) talk to the telldusd daemon through a local socket, so the daemon is required at run time to actually reach a Tellstick. Only the client library and its header are installed here; the telldusd daemon needs libftdi and libconfuse and is not part of this package. https://github.com/telldus/telldus
