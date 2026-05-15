# snapcast 0.35.0
  - Homepage: [https://github.com/badaix/snapcast](https://github.com/badaix/snapcast)
  - Manpage: [https://github.com/badaix/snapcast#readme](https://github.com/badaix/snapcast#readme)
  - Changelog: [https://github.com/badaix/snapcast/releases](https://github.com/badaix/snapcast/releases)
  - Repository: [https://github.com/badaix/snapcast](https://github.com/badaix/snapcast)
  - Package: [master/make/pkgs/snapcast/](https://github.com/Ircama/freetz-evo/tree/master/make/pkgs/snapcast/)
  - Steward: Ircama

  - Depends on: `alsa-lib`, `flac`, `libogg`, `libvorbis`, `openssl`
  - Provides: `/usr/bin/snapserver`, `/usr/bin/snapclient`, `/etc/snapserver.conf`, `/usr/share/snapserver`
  - Externalization: supported

`snapcast` is a multiroom audio distribution system made of a central `snapserver` plus one or more `snapclient` receivers. This Freetz-EVO package is a binary-first port intended for manual setup on embedded targets.

The packaged feature set keeps the core embedded use case: ALSA output for `snapclient`, FLAC and Ogg/Vorbis support, and OpenSSL-enabled networking. Upstream features that would add noticeable dependency weight on the box are left off in this first port.

## Included feature set

- `snapserver` and `snapclient` upstream binaries in one package
- default `snapserver.conf` installed under `/etc`
- shared web and helper assets under `/usr/share/snapserver`
- ALSA output backend enabled for `snapclient`
- FLAC and Ogg/Vorbis codec support enabled

## Deliberately disabled upstream features

- mDNS discovery via Avahi
- Opus codec support
- PulseAudio, JACK, PipeWire, and SDL2 backends
- upstream tests and manpage/pixmap payload at install time

## Practical usage

This initial Freetz-EVO port does not add a dedicated CGI yet. Configure `snapserver` through `/etc/snapserver.conf` and start the binaries manually or from your own local service wrapper.