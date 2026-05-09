# hey 0.1.5 (HTTP load generator)
  - Homepage: [https://github.com/rakyll/hey](https://github.com/rakyll/hey)
  - Manpage / README: [https://github.com/rakyll/hey#readme](https://github.com/rakyll/hey#readme)
  - Changelog: [https://github.com/rakyll/hey/releases](https://github.com/rakyll/hey/releases)
  - Repository: [https://github.com/rakyll/hey](https://github.com/rakyll/hey)
  - Package: [../../make/pkgs/hey/](../../make/pkgs/hey/)
  - Steward: Ircama

`hey` is a small HTTP benchmarking tool for generating concurrent request load
against web services hosted on the FritzBox or elsewhere on the network.

## Runtime details in Freetz

- Binary path: `/usr/bin/hey`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary

## Build notes

- The package cross-compiles the upstream Go sources into a single target executable.
- No external helper tools are required for its basic benchmarking mode.

## Typical usage

```sh
hey -n 100 -c 10 http://127.0.0.1:8080/
```

Notes:
- On embedded targets, use conservative concurrency values to avoid self-inflicted overload.
- `hey` is useful for smoke-testing local CGI or web UI endpoints after package changes.