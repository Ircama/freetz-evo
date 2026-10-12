# Native Matter Controller

`src/server.rs` builds the production `matter-bridge` daemon, embedding
PASE/CASE, interviews, subscriptions, persistent fabric and WebSocket API.
Domoticz needs this one service, not a second controller process or IPC.
See [setup and limitations](../../../../docs/make/matter-bridge.md).

`src/main.rs` builds `matter-bridge-ctl`, a standalone diagnostic commissioner
that creates a fresh fabric per invocation. It is not the daemon backend.
Do not use the production daemon's store for diagnostic commissioning.

```sh
matter-bridge --port 5580 --bind 127.0.0.1 \
  --store /tmp/flash/matter-bridge --peer '[::1]:5540' --auto-local
CARGO_BUILD_JOBS=1 cargo +nightly check --locked --bins
CARGO_BUILD_JOBS=1 cargo +nightly build --locked --release --bin matter-bridge
```

rs-matter is pinned to `7d5684f495fe5bca03d993647543508ab7587f10`.
The Freetz recipe builds both binaries with Rust nightly, Cargo.lock,
package-local uClibc dependency patches and serialized compilation.

The local accessory needs no multicast discovery or network provisioning.
Production Device Attestation verification is missing upstream; local
commissioning accepts the test certificate only on loopback by default.