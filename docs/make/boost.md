# Boost 1.87.0
  - Package: [master/make/libs/boost/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/boost/)
  - Homepage: [https://www.boost.org/](https://www.boost.org/)
  - Changelog: [https://www.boost.org/users/history/](https://www.boost.org/users/history/)
  - Repository: [https://github.com/boostorg/boost](https://github.com/boostorg/boost)
  - Provides: `libboost_thread.so`, `libboost_system.so` — portable C++ source libraries (full header tree included)
  - Used by: Domoticz (Boost.Asio, Boost.Signals2, Boost.Thread)
  - Externalization: supported

Boost provides free, peer-reviewed and portable C++ source libraries. This package installs the complete Boost header tree plus the shared libraries that current Freetz-EVO C++ packages need: `thread` (depends on `libpthread`) and `system`.

## Build notes

- Boost is cross-built from source with **b2 (Boost.Build)**, following the same pattern already used in this tree by the PowerDNS packages (`pdns-recursor`, `pdns-authoritative`, `pdns-dnsdist`):
  - `./bootstrap.sh --with-libraries=thread,system` runs with the **host** compiler (`CC=gcc CXX=g++`), because b2 itself is a build host tool.
  - The cross compiler is described in a generated `user-config.jam`:
    `using gcc : : $(TARGET_CXX) : <archiver>$(TARGET_AR) <ranlib>$(TARGET_RANLIB) <compileflags>"$(TARGET_CFLAGS) -fPIC" <linkflags>"$(TARGET_LDFLAGS)" ;`
  - The per-architecture b2 properties come from `config/mod/boost.in` (`FREETZ_TARGET_B2_ARCH_OPTS`, e.g. `architecture=mips address-model=32 binary-format=elf abi=o32` for MIPS) and are combined with `target-os=linux variant=release threading=multi cxxstd=17 --layout=system`.
- The package requires **uClibc 1.0.58 or newer** (`FREETZ_TARGET_UCLIBC_1_0_58_MIN` in `Config.in`): Boost 1.87 needs C++14/17 and a modern NPTL toolchain.
- Only the `thread` and `system` components are built by default; add further components to `$(PKG)_B2_LIBRARIES` and provide a matching `<component>-config.cmake`.

## CMake integration

Boost is consumed through **CMake package config mode**:

```cmake
find_package(Boost CONFIG REQUIRED COMPONENTS thread)
target_link_libraries(myapp PRIVATE Boost::thread)
```

CMake 4.x removed the `FindBoost` module, which is why this package installs hand-written package config files (`files/cmake/BoostConfig.cmake`, `boost_thread-config.cmake`, `boost_system-config.cmake`) into

```
<staging-prefix>/usr/lib/cmake/Boost-1.87.0/
```

The components declared there are exactly the ones built (`thread`, `system`); `Boost::thread` pulls in `Boost::system` automatically.

## Configuration symbols

- `FREETZ_LIB_libboost_thread` (visible) — installs `libboost_thread.so` and selects `FREETZ_LIB_libboost_system`.
- `FREETZ_LIB_libboost_system` (hidden) — `libboost_system.so`, selected together with Boost.Thread and installing `FREETZ_LIB_libpthread` when the target has multiple libraries.

Both support externalization (`external.in` / `external.files`), so the libraries can be placed on USB/NAS storage.
