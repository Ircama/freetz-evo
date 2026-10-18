# InfluxDB 3.12.1 (experimental port)
  - Homepage: [https://www.influxdata.com/](https://www.influxdata.com/)
  - Changelog: [https://github.com/influxdata/influxdb/releases](https://github.com/influxdata/influxdb/releases)
  - Repository: [https://github.com/influxdata/influxdb](https://github.com/influxdata/influxdb)
  - Package: [master/make/pkgs/influxdb3/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/influxdb3/)
  - Steward: Ircama

## Freetz service

The package includes `/etc/init.d/rc.influxdb3` and the configuration page
`/cgi-bin/conf/influxdb3`. The service is **disabled by default**. Its default
HTTP listener is `127.0.0.1:8181`, with authentication enabled.

1. Prepare an existing writable directory on local external storage, preferably
   ext4, such as `/var/media/ftp/USB/influxdb3-data`. Replace `USB` with the actual
   mount. Database files are not part of the `modsave` configuration archive.
2. Open the InfluxDB 3 configuration page. Select the data directory, a stable
   node ID, bind address and port.
3. Choose automatic startup if wanted, save and explicitly start/restart the
   service. **Save does not restart it.**
4. With authentication enabled, create the initial administrator token using
   the upstream CLI (`influxdb3 create token --admin` for the default endpoint).
   Keep the token private and pass it to clients; do not put it in service logs.

Service settings are exported in `/mod/etc/default.influxdb3/influxdb3.cfg`
and persisted through modconf in `/mod/etc/conf/influxdb3.cfg`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `INFLUXDB3_ENABLED` | `no` | Manual/automatic startup |
| `INFLUXDB3_NODE_ID` | `fritz` | Stable node identifier; changing it does not migrate existing data |
| `INFLUXDB3_DATA_DIR` | empty | Existing writable database directory; required before enabling |
| `INFLUXDB3_BIND` | `127.0.0.1` | Numeric IPv4 or IPv6 address, without IPv6 brackets |
| `INFLUXDB3_PORT` | `8181` | HTTP port |
| `INFLUXDB3_WITHOUT_AUTH` | `no` | Explicitly opt out of authentication; unsafe on untrusted networks |
| `INFLUXDB3_CONFIG_WAIT` | `120` | Boot wait for executable and storage, in seconds; `0` starts synchronously |
| `INFLUXDB3_STARTUP_WAIT` | `60` | HTTP health-check startup timeout, in seconds |

Boot resource waiting runs in the background and does not block Freetz startup.
Manual start fails immediately if the executable or writable directory is
missing. Parent/data directories are not created automatically, avoiding
accidental writes to internal storage before a USB mount is available. Startup
checks `/health` and reports failures; logs are in `/tmp/rc.influxdb3.log`.
Stop/restart cancels pending boot waiting, and shutdown gives the server up to
60 seconds to exit gracefully.

```sh
/etc/init.d/rc.influxdb3 start
/etc/init.d/rc.influxdb3 status
/etc/init.d/rc.influxdb3 stop
/etc/init.d/rc.influxdb3 restart
```

The executable can be externalized to `/mod/external/usr/bin/influxdb3`.
The RC script also finds that path when the ordinary executable link is absent.
There is no database-query/dashboard UI bundled with this package: the Freetz
CGI configures the service, while data access uses InfluxDB APIs and CLI.

## Build and recompile

```sh
make influxdb3-precompiled
make influxdb3-recompile
```

`-recompile` uses the standard Freetz distclean/precompiled sequence, including
binary installation and the usual package progress/`done.` messages. Cargo
downloads and dependency artifacts are retained in
`build/cargo-influxdb3-cache/<version>-<target>`; clean removes the final cached
executable even when the source workspace was already removed.
`make influxdb3-cargo-clean` explicitly removes the compilation cache when a
full Cargo rebuild is intended. Do not run concurrent builds of this package.

The ELF interpreter is chosen at link time. Installation strips the executable
without rewriting its interpreter using patchelf, which caused corrupt MIPS
program headers in earlier tests.

## Unsupported or unverified components

This remains an **experimental port**, not a certified compatibility matrix.

| Component | Status |
|-----------|--------|
| WASM SQL UDFs on targets without native 64-bit atomics, including MIPS | Unsupported; requests fail explicitly because required Wasmtime epoch interruption is unavailable |
| WASM on native-64-bit-atomic targets | Original upstream path retained, not validated by the MIPS smoke test |
| Embedded Python processing engine/plugins | Compiled into the server; plugin execution is not covered by the database smoke test |
| Optional top-level cloud backends, large-string-offset and jemalloc features | Not enabled by this build; transitive cloud libraries may still be present |
| Remote object stores | Not configured by the Freetz service, which explicitly uses `--object-store file`; not validated by local-storage tests |
| Flux | Not provided by InfluxDB 3 Core; use SQL or InfluxQL |
| Other Freetz architectures | Rust target mappings exist; selection does not certify build/runtime support |

MIPS big-endian testing exposed additional Arrow/Parquet errors after the
original basic smoke test. Corrective overrides and an exact-value regression
are included; passing a simple write/count query alone does not certify bitmap
filtering, sparse values, Parquet snapshots or old-data recovery. See the
[package status and endian regression procedure](../../make/pkgs/influxdb3/README.md#big-endian-regression-checks).
Files written with a defective older encoder are not automatically repaired.
The latest rebuilt MIPS candidate still fails the exact attribute-filter
regression despite preserving the expected row count: query correctness remains
unresolved. Do not treat this CLI smoke test as production validation.

## CLI smoke test

Use a **separate terminal** to start this foreground test server:

```sh
influxdb3 serve --node-id fritz-test --object-store file --data-dir /tmp/influxdb3-test --http-bind 127.0.0.1:8181 --without-auth
```

Then run:

```sh
wget -S -O - http://127.0.0.1:8181/health
wget -S -O - --post-data='temperature,room=dining value=20.5' 'http://127.0.0.1:8181/api/v3/write_lp?db=test&precision=auto'
wget -q -O - 'http://127.0.0.1:8181/api/v3/query_sql?db=test&q=SELECT%20*%20FROM%20temperature'
```

Expect a successful health response, a successful write and one result with
`room=dining` and `value=20.5`. The write response may have an empty body.
Run the write only once if expecting exactly one row: each timestamp-less
write creates a new reception timestamp.

If port 8181 is already occupied, use a free port in **all four commands**;
do not interrupt a production server merely to run this test. If necessary use
`/mod/external/usr/bin/influxdb3` for the executable. Stop the foreground server
with Ctrl+C after testing.

`/tmp/influxdb3-test` is a small, disposable RAM-backed diagnostic store, not a
production storage recommendation. The `--without-auth` flag is for this
isolated loopback test only. For continuous collection use persistent suitable
storage and authentication, and perform exact-value/persistence regressions.
