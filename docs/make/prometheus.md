# prometheus 3.11.3 (monitoring server)
  - Homepage: [https://prometheus.io/](https://prometheus.io/)
  - Manpage / README: [https://prometheus.io/docs/prometheus/latest/](https://prometheus.io/docs/prometheus/latest/)
  - Changelog: [https://github.com/prometheus/prometheus/releases](https://github.com/prometheus/prometheus/releases)
  - Repository: [https://github.com/prometheus/prometheus](https://github.com/prometheus/prometheus)
  - Package: [../../make/pkgs/prometheus/](../../make/pkgs/prometheus/)
  - Steward: Ircama

`prometheus` is a monitoring and alerting server that scrapes metrics endpoints,
stores time series data, and exposes a query UI and HTTP API.

## Runtime details in Freetz

- Binary path: `/usr/bin/prometheus`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary
- Typical storage location: configuration and TSDB data should be placed on writable USB or NAS media

## Build notes

- The package builds the upstream `./cmd/prometheus` server binary.
- Embedded TSDB data can grow quickly, so flash-internal storage is usually a poor fit.

## Typical usage

```sh
prometheus \
  --config.file=/var/media/ftp/uStor01/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/media/ftp/uStor01/prometheus/data
```

Notes:
- Prometheus is most practical when paired with explicit scrape targets on the LAN.
- Keep retention, WAL, and query load conservative on smaller routers.