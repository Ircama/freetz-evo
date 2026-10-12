# openzwave: libopenzwave (libopenzwave.so) 1.6
  - Homepage: [https://github.com/OpenZWave/open-zwave](https://github.com/OpenZWave/open-zwave)
  - Changelog: [https://github.com/OpenZWave/open-zwave/releases](https://github.com/OpenZWave/open-zwave/releases)
  - Repository: [https://github.com/OpenZWave/open-zwave](https://github.com/OpenZWave/open-zwave)
  - Library: [master/make/libs/openzwave/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/openzwave/)
  - Steward: -

OpenZWave is a C++ library that provides an interface to the Z-Wave home automation protocol. It talks to the controller stick through a plain serial device (/dev/ttyUSB*, /dev/ttyACM*), so it does not need libusb; the bundled hidapi back end (and with it libudev) stays disabled on this target. The Z-Wave device database lives in Domoticz's own Config directory, which is why it is not installed twice. The Domoticz package points its build at this library explicitly, because its own detection would not find the headers in usr/include/openzwave. This is the master branch of OpenZWave, not the v1.6 release: Domoticz includes ValueIDIndexesDefines.h, a header that the release predates. The commit is pinned, the build is the same as the release one (same soname, same install layout).
