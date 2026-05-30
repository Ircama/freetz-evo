# yaml-cpp 0.8.0
  - Homepage: [https://github.com/jbeder/yaml-cpp](https://github.com/jbeder/yaml-cpp)
  - Changelog: [https://github.com/jbeder/yaml-cpp/releases](https://github.com/jbeder/yaml-cpp/releases)
  - Repository: [https://github.com/jbeder/yaml-cpp](https://github.com/jbeder/yaml-cpp)
  - Package: [../../make/libs/yaml-cpp/](../../make/libs/yaml-cpp/)

  - Provides: `libyaml-cpp.so.0.8.0`
  - Externalization: supported

yaml-cpp is a C++ library for parsing and emitting YAML configuration files.

## Typical consumers

- PowerDNS `geoip` backend
- PowerDNS `ixfrdist`
- other C++ packages needing a shared YAML parser/emitter runtime

## Notes

The Freetz-EVO package builds the shared library with CMake, disables upstream
tests and tools, and keeps headers plus CMake/pkg-config metadata in staging for
cross-build users.