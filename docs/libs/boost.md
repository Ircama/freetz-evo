# boost (headers, libboost_thread, libboost_system) 1.87.0
  - Homepage: [https://www.boost.org/](https://www.boost.org/)
  - Changelog: [https://www.boost.org/users/history/](https://www.boost.org/users/history/)
  - Repository: [https://github.com/boostorg/boost](https://github.com/boostorg/boost)
  - Library: [master/make/libs/boost/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/libs/boost/)
  - Steward: [@Ircama](https://github.com/Ircama)

Boost 1.87.0 C++ libraries, cross-built with b2 exactly like the Boost copy bundled in this tree by the pdns-recursor package. Installs the complete Boost header tree below /usr/include/boost plus: - libboost_thread.so (Boost.Thread, requires nptl pthreads) - libboost_system.so (Boost.System) A minimal CMake package config is installed into the staging prefix as well, because CMake 4.x no longer ships the FindBoost module. CMake based consumers therefore use: find_package(Boost CONFIG REQUIRED COMPONENTS thread) Required by the Domoticz package (Boost.Asio, Boost.Signals2 and Boost.Thread are used throughout its source).
