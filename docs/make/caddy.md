# caddy 2.11.2 (binary only)
  - Homepage: [https://caddyserver.com/](https://caddyserver.com/)
  - Manpage: [https://caddyserver.com/docs/](https://caddyserver.com/docs/)
  - Changelog: [https://github.com/caddyserver/caddy/releases](https://github.com/caddyserver/caddy/releases)
  - Repository: [https://github.com/caddyserver/caddy](https://github.com/caddyserver/caddy)
  - Package: [master/make/pkgs/caddy/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/caddy/)
  - Steward: Ircama

`caddy` is a general-purpose web server, reverse proxy, and static file server.
Upstream enables automatic HTTPS by default, but on a FRITZ!Box it is usually best
to keep the configuration, certificates, and runtime state on writable external
storage.

## Runtime details in Freetz

- Binary path: `/usr/bin/caddy`
- Runtime dependency profile: self-contained Go binary built with `CGO_ENABLED=0`
- Externalization: supported for the binary
- Default service integration: none; the package installs the executable only

## Build notes

- The package cross-compiles the upstream Go sources into a single target binary.
- Go modules are downloaded into a package-local build cache during compilation.
- No init script, default `Caddyfile`, or web interface integration is installed.

## Typical usage

```sh
mkdir -p /var/media/ftp/uStor01/caddy/{config,data,site}
cat >/var/media/ftp/uStor01/caddy/Caddyfile <<'EOF'
:8080 {
    root * /var/media/ftp/uStor01/caddy/site
    file_server
}
EOF

XDG_CONFIG_HOME=/var/media/ftp/uStor01/caddy/config \
XDG_DATA_HOME=/var/media/ftp/uStor01/caddy/data \
caddy run --config /var/media/ftp/uStor01/caddy/Caddyfile
```

Notes:
- Prefer writable external storage for the `Caddyfile`, certificate cache, and logs.
- Automatic HTTPS and ACME validation only work when the box is reachable on the
  required ports and has valid DNS pointing to it.
- Port 81 is already used by the Freetz web UI; choose alternate listen ports or
  place `caddy` behind another reverse-proxy setup.