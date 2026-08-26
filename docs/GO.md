# Freetz-EVO — Go Cross-Compilation

Freetz-EVO adds cross-compilation support for Go packages, enabling a collection of modern Go-based command-line and daemon tools to run on FRITZ!Box devices. The implementation centres on a host-tool (`go-host`) that downloads a pre-built Go toolchain and exposes it to the build system, plus a set of per-package conventions for isolation, architecture mapping, and CGO handling.

All relevant options are available under **Packages** in `make menuconfig`.

---

## go-host — the host toolchain

`make/host-tools/go-host/` downloads the official pre-built **Go 1.25.10 linux-amd64** tarball from the Go project mirrors and installs it into `$(TOOLS_DIR)/go-host/`. The installation copies the `bin/`, `src/`, `pkg/`, `lib/`, and `go.env` trees from the extracted archive into the tools directory. No patching or recompilation of the Go toolchain is needed — the official linux-amd64 build supports all cross-compilation scenarios required by Freetz-EVO targets.

After `go-host` is built, the Go compiler is available at `$(TOOLS_DIR)/go-host/bin/go` and all package makefiles can reference it through that fixed path.

---

## Cross-compilation model

Go's native cross-compilation support makes porting relatively straightforward. The key environment variables are:

**`GOOS=linux`** — constant for all FRITZ!Box targets.

**`GOARCH`** — mapped from Freetz's `FREETZ_TARGET_ARCH` via the `FREETZ_TARGET_GO_ARCH` variable. Supported mappings: `mips`, `mipsle` (little-endian MIPS), `386` (32-bit x86), `arm`, and `arm64` (aarch64).

**`GOMIPS=softfloat`** — set for all MIPS targets because FRITZ!Box MIPS CPUs lack a hardware floating-point unit and uClibc is built without hard-float ABI.

**`GOARM=5`** — set for 32-bit ARM targets to select the ARMv5 (software float) ABI, matching the uClibc build.

**`-tags netgo`** — passed to `go build` for most packages. This build tag instructs the Go runtime to use its pure-Go DNS resolver instead of linking against `libresolv`. `libresolv` is part of glibc and is absent from uClibc, so packages that do any DNS resolution must use `netgo` to avoid a link error.

**`CGO_ENABLED`** — set to `1` for packages that require C library integration (see CGO below), and to `0` for pure-Go packages. Disabling CGO produces fully static binaries that do not depend on any shared libraries.

### Build isolation

Each Go package gets its own private **`GOMODCACHE`** and **`GOCACHE`** directories under `$(PKG_DIR)/go-cache/`. This prevents module cache contention when multiple packages build in parallel and ensures reproducible builds: a package's module downloads are committed alongside the source and not shared with other packages.

### GCC version gate

Go 1.25 requires **GCC 4.7 or newer** for its CGO runtime, which uses C11 atomic operations. A build-time check in the package infrastructure verifies the host GCC version before enabling CGO.

---

## CGO packages

Most Go packages build with CGO disabled and link only the Go standard library. A few packages require CGO:

**go-librespot** is the primary example of a CGO package in Freetz-EVO. It implements the Spotify Connect protocol and audio playback, requiring C libraries for audio output (`libavcodec`, `libavformat`, ALSA) and for the Shannon cipher used by the Spotify protocol (`libshannenc`). Its package makefile sets `CGO_ENABLED=1`, exports the sysroot and cross-compiler paths for `cgo`, and links against the pre-built cross libraries via `CGO_CFLAGS` and `CGO_LDFLAGS`.

For CGO packages, the cross-compilation linker must be the target GCC (not the host GCC), and the `CC` variable must point to the Freetz cross-compiler. The Go toolchain passes `CC` through to `cgo` automatically when `CGO_ENABLED=1`.

---

## Go package collection

The following Go packages are available in Freetz-EVO. All are EVO-only additions unless noted.

| Package | Version | CGO | Description |
|---|---|---|---|
| `go-librespot` | 0.1.3 | Yes | Spotify Connect receiver and player |
| `lazygit` | 0.45.0 | No | TUI Git interface |
| `hugo` | 0.147.9 | No | Static site generator |
| `rclone` | 1.70.0 | No | Cloud storage sync (S3, Drive, Dropbox, …) |
| `fzf` | 0.61.1 | No | Fuzzy finder for the terminal |
| `hey` | 0.1.4 | No | HTTP load testing tool |
| `caddy` | 2.10.0 | No | HTTP/2 web server with automatic TLS |
| `gh` | 2.73.0 | No | GitHub CLI |
| `prometheus` | 3.4.1 | No | Monitoring and alerting toolkit |
| `lf` | r35 | No | Terminal file manager |
| `age` | 1.1.0 | No | Simple, modern file encryption |
| `restic` | 0.17.3 | No | Fast, encrypted backup tool |
| `vhs` | 0.9.0 | No | Terminal GIF recorder |

Versions reflect the state at the most recent Freetz-EVO release; they are updated regularly as upstream projects release new versions.

---

## Porting a new Go package

A minimal Go package makefile sets the version, source URL, and calls `go build` with the Freetz cross-compilation environment. The key elements are:

```makefile
$(PKG)_CONFIGURE_ENV := \
    GOOS=linux \
    GOARCH=$(FREETZ_TARGET_GO_ARCH) \
    GOMIPS=softfloat \
    GOMODCACHE=$($(PKG)_DIR)/go-cache/mod \
    GOCACHE=$($(PKG)_DIR)/go-cache/build \
    CGO_ENABLED=0

$(PKG)_CONFIGURE_CMDS := \
    $($(PKG)_CONFIGURE_ENV) \
    $(TOOLS_DIR)/go-host/bin/go build \
        -tags netgo \
        -ldflags '-s -w' \
        -o $($(PKG)_DIR)/$(PKG_BINARY_NAME) \
        ./cmd/$(PKG_NAME)
```

For CGO packages, set `CGO_ENABLED=1` and add `CC=$(TARGET_CC)`, `CGO_CFLAGS=$(TARGET_CFLAGS)`, and `CGO_LDFLAGS=$(TARGET_LDFLAGS)` to the configure environment. Verify that all required C libraries are available as cross-compiled Freetz packages and listed as dependencies.

Packages that perform DNS lookups must use `-tags netgo` — omitting it will produce a binary that fails to resolve hostnames on uClibc because `libresolv.so` is absent.
