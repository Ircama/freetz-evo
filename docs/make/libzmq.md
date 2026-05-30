# libzmq 4.3.5
  - Homepage: [https://zeromq.org/](https://zeromq.org/)
  - Changelog: [https://github.com/zeromq/libzmq/releases](https://github.com/zeromq/libzmq/releases)
  - Repository: [https://github.com/zeromq/libzmq](https://github.com/zeromq/libzmq)
  - Package: [../../make/libs/libzmq/](../../make/libs/libzmq/)

  - Provides: `libzmq.so.5.2.5`
  - Externalization: supported

libzmq is the core ZeroMQ messaging library for lightweight asynchronous
request/reply, pub/sub, and brokerless messaging patterns.

## Typical consumers

- PowerDNS remotebackend with optional ZeroMQ connector
- target daemons exposing ZeroMQ control or transport endpoints

## Notes

The Freetz-EVO build keeps the runtime focused: drafts, Curve support, PGM,
NORM, VMCI, and libsodium integration are disabled in this package recipe.