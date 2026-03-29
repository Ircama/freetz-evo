# llama.cpp — b8575

| | |
|---|---|
| **Homepage** | [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| **Changelog** | [github.com/ggml-org/llama.cpp/releases](https://github.com/ggml-org/llama.cpp/releases) |
| **Repository** | [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| **Package** | [`make/pkgs/llama-cpp/`](../../make/pkgs/llama-cpp/) |
| **Maintainer** | @Ircama |

---

## Overview

**llama.cpp** is a high-performance, pure-C/C++ LLM inference engine that runs
quantized GGUF language models entirely on the CPU — no GPU, CUDA, or driver
stack required.

The Freetz-EVO package cross-compiles llama.cpp to **MIPS32** for the FRITZ!Box.
It uses the CMake build system with shared libraries (`libllama.so`, `libggml*.so`)
so that multiple tools share a single copy of the inference code, keeping total
storage usage manageable on a 100 MB device.

### Practical device constraints

| Resource | Value | Impact |
|---|---|---|
| Storage | ~100 MB | All binaries + libs must fit; models go to USB/NAS |
| RAM | 512 MB | Practical model limit: Q4_K_M ≤ ~400 MB |
| CPU cores | 4 × MIPS34Kc | Use `--threads 4` for maximum throughput |
| GPU | none | `--n-gpu-layers 0` (always) |

### Recommended models for this device

| Model | GGUF quantisation | Size | RAM usage |
|---|---|---|---|
| SmolLM2-360M | Q4_K_M | ~220 MB | ~280 MB |
| Qwen2.5-0.5B-Instruct | Q4_K_M | ~350 MB | ~420 MB |
| SmolLM2-1.7B | Q4_K_M | ~1.1 GB | too large |

Inference speed on MIPS34Kc (single-threaded) is ~1–5 tokens/s depending on model
size and quantisation. Enable threading (`-t 4`) for better throughput.

---

## Installation

Enable the package in `make menuconfig` under:

```
Packages → L → llama.cpp
```

Optional tools and server features can be selected within the `llama.cpp` submenu:

```
[*] llama.cpp b8575 (LLM inference engine)
    --- Optional tools
    [ ] llama-bench          — performance benchmark
    [ ] llama-perplexity     — model quality measurement
    [ ] llama-tokenize       — tokenizer diagnostic
    [ ] llama-imatrix        — importance matrix for smart quantisation
    [ ] llama-gguf-split     — split/merge multi-shard GGUF files
    [ ] llama-batched-bench  — batched inference benchmark
    [ ] llama-tts            — text-to-speech (OuteTTS)
    [ ] llama-mtmd-cli       — multimodal (vision) inference
    --- llama-server options
    [ ] Enable HTTPS (OpenSSL) support in llama-server
    [ ] Embed built-in web UI in llama-server (~2 MB extra)
```

---

## What gets installed

| Item | Location |
|---|---|
| `llama-cli` | `/usr/bin/llama-cli` |
| `llama-server` | `/usr/bin/llama-server` |
| `llama-quantize` | `/usr/bin/llama-quantize` |
| Optional tools | `/usr/bin/llama-*` |
| `libllama.so` | `/usr/lib/libllama.so` |
| `libggml.so`, `libggml-cpu.so`, … | `/usr/lib/libggml*.so*` |
| Init script | `/etc/init.d/rc.llama-cpp` |
| Default config | `/mod/etc/default.llama-cpp/llama-cpp.cfg` |

All binaries and shared libraries are **strongly recommended for externalisation**
(total size can be 40–80 MB stripped). The externalization submenu is pre-enabled
with `default y` for both binaries and libraries.

---

## Quick start

### 1. Place a GGUF model on USB storage

```bash
# On the FRITZ!Box, after USB drive mounts
mkdir -p /var/media/ftp/llama-cpp
# Copy a model file there (e.g. via SCP)
scp qwen2.5-0.5b-instruct-q4_k_m.gguf root@fritz.box:/var/media/ftp/llama-cpp/
```

### 2. Configure via the Freetz web UI

Go to `http://fritz.box:81/ → Packages → llama.cpp` and set:

| Field | Example |
|---|---|
| Base directory | `/var/media/ftp/llama-cpp` |
| Model path | `/var/media/ftp/llama-cpp/qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Host | `0.0.0.0` |
| Port | `8080` |
| Threads | `4` |
| Context size | `512` ← reduce if RAM is tight |
| Enabled | `yes` |

### 3. Start the server

```bash
/etc/init.d/rc.llama-cpp start
# or restart the web UI page and let it start at next boot
```

### 4. Run inference

```bash
# Interactive CLI (on the device itself)
llama-cli -m /var/media/ftp/llama-cpp/model.gguf \
          -p "Explain quantum computing in one paragraph" \
          -n 200 -t 4 --no-display-prompt

# REST API from a client on the same LAN
curl http://fritz.box:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'

# Check server health
curl http://fritz.box:8080/health
```

---

## Runtime configuration

The init script and Freetz web UI expose these settings:

| Variable | Default | Description |
|---|---|---|
| `LLAMA_CPP_ENABLED` | `no` | Auto-start at boot |
| `LLAMA_CPP_BASEDIR` | `/var/media/ftp/llama-cpp` | Base directory for models |
| `LLAMA_CPP_MODEL` | *(empty)* | Path to GGUF model (optional at startup) |
| `LLAMA_CPP_HOST` | `0.0.0.0` | Bind address |
| `LLAMA_CPP_PORT` | `8080` | HTTP port |
| `LLAMA_CPP_THREADS` | `4` | Number of inference threads |
| `LLAMA_CPP_CTX_SIZE` | `2048` | Context size in tokens |
| `LLAMA_CPP_NGL` | `0` | GPU layers (must be 0, no GPU) |
| `LLAMA_CPP_PARALLEL` | `1` | Simultaneous client slots |
| `LLAMA_CPP_EXTRA_ARGS` | *(empty)* | Extra `llama-server` flags |
| `LLAMA_CPP_CONFIG_WAIT` | `120` | Boot wait time (0 = sync start) |
| `LLAMA_CPP_NICE` | `5` | Nice priority |

All variables are persisted in `/mod/etc/conf/llama-cpp.cfg`.

---

## Using llama-quantize

`llama-quantize` converts full-precision or half-precision GGUF files to smaller
quantised formats:

```bash
# Q4_K_M is the best quality/size tradeoff for most models
llama-quantize model-f16.gguf model-q4_k_m.gguf Q4_K_M

# Q4_K_M with importance matrix for higher quality
llama-imatrix -m model-f16.gguf -f calibration_data.txt -o imatrix.dat
llama-quantize --imatrix imatrix.dat model-f16.gguf model-q4_k_m.gguf Q4_K_M
```

Quantisation is CPU-intensive and takes significant time on MIPS. It is usually
more practical to quantise on a host PC and copy the resulting GGUF to the device.

---

## Build details

### CMake cross-compilation

The package uses `$(PKG_CONFIGURED_CMAKE)` with the following key flags:

| CMake flag | Value | Reason |
|---|---|---|
| `CMAKE_SYSTEM_NAME` | `Linux` | Explicit cross-compile target |
| `CMAKE_SYSTEM_PROCESSOR` | `mips` | Target architecture |
| `CMAKE_C_COMPILER` | `$(TARGET_CC)` | MIPS cross-compiler |
| `CMAKE_CXX_COMPILER` | `$(TARGET_CXX)` | MIPS C++ cross-compiler |
| `GGML_NATIVE` | `OFF` | **Critical**: prevents `-march=native` from using host CPU |
| `BUILD_SHARED_LIBS` | `ON` | Shared libs save storage vs. static-linked copies per tool |
| `LLAMA_BUILD_EXAMPLES` | `OFF` | Reduces build time; tools cover all needed functionality |
| `LLAMA_BUILD_TESTS` | `OFF` | No test framework on device |
| All GPU backends | `OFF` | FRITZ!Box has no GPU |

### No submodule issue

At tag `b8575`, llama.cpp has an **empty `.gitmodules`** — all ggml source code
is inlined directly in the `ggml/` directory of the main repository. The GitHub
archive tarball at the commit hash therefore contains everything needed; no
secondary downloads are required.

### Shared libraries and storage

The CMake build produces:
- `libggml.so`, `libggml-cpu.so`, and related ggml libraries
- `libllama.so` (llama API layer)

Each tool binary links against these shared libraries, so the per-binary overhead
is small (~1–5 MB stripped each for most tools). Total storage including all shared
libraries is typically 40–80 MB stripped. Externalisation to the external filesystem
(SquashFS or ext2 partition) is strongly recommended.

### Model storage

Models are NOT part of the firmware image. They must be on writable external
storage (USB hard drive or USB flash drive, preferably formatted as ext4).
The `LLAMA_CPP_BASEDIR` configuration variable points to the model directory.

---

## Relevant files

| File | Purpose |
|---|---|
| [`make/pkgs/llama-cpp/llama-cpp.mk`](../../make/pkgs/llama-cpp/llama-cpp.mk) | Package makefile: download, CMake configure, build, install |
| [`make/pkgs/llama-cpp/Config.in`](../../make/pkgs/llama-cpp/Config.in) | Kconfig: main package + optional tools + server options |
| [`make/pkgs/llama-cpp/external.in`](../../make/pkgs/llama-cpp/external.in) | Externalisation config (binaries and shared libraries) |
| [`make/pkgs/llama-cpp/external.files`](../../make/pkgs/llama-cpp/external.files) | List of files to externalise |
| [`make/pkgs/llama-cpp/files/root/etc/init.d/rc.llama-cpp`](../../make/pkgs/llama-cpp/files/root/etc/init.d/rc.llama-cpp) | Init script: start/stop/status for llama-server |
| [`make/pkgs/llama-cpp/files/root/mod/etc/default.llama-cpp/llama-cpp.cfg`](../../make/pkgs/llama-cpp/files/root/mod/etc/default.llama-cpp/llama-cpp.cfg) | Default configuration (all exported variables) |
| [`make/pkgs/llama-cpp/files/root/mod/etc/default.llama-cpp/llama-cpp.save`](../../make/pkgs/llama-cpp/files/root/mod/etc/default.llama-cpp/llama-cpp.save) | Save hooks (pre/apply) for the modconf web UI |
