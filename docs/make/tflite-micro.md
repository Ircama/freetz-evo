# tflite-micro (TFLM) — 20260318

| | |
|---|---|
| **Homepage** | [github.com/tensorflow/tflite-micro](https://github.com/tensorflow/tflite-micro) |
| **Changelog** | [CHANGELOG.md](https://github.com/tensorflow/tflite-micro/blob/main/CHANGELOG.md) |
| **Repository** | [github.com/tensorflow/tflite-micro](https://github.com/tensorflow/tflite-micro) |
| **Package** | [`make/pkgs/tflite-micro/`](../../make/pkgs/tflite-micro/) |
| **Maintainer** | @Ircama |

---

## Overview

**TensorFlow Lite for Microcontrollers (TFLM)** is Google's purpose-built runtime for machine learning
inference on resource-constrained devices — originally targeting bare-metal microcontrollers, and fully
capable of running on embedded Linux platforms like the FRITZ!Box.

The Freetz-EVO package cross-compiles TFLM into a **static library** (`libtflm.a`) for MIPS32, along
with 200+ C++ headers, making the full inference engine available to other packages at link time.
No Python runtime is needed on the device — the library is entirely self-contained.

Supported operations include the complete TFLM kernel set: convolutions (conv2d, depthwise conv,
transpose conv), pooling, LSTM, GRU, fully connected layers, softmax/sigmoid/tanh activations,
reshape, concatenation, dequantize, and more.

## Installation

Enable the package in `make menuconfig` under:

```
Packages → T → tflite-micro [*]
```

An optional sub-option builds and installs a demo binary:

```
[*] Build hello_world demo binary
```

## What Gets Installed

| Item | Location |
|---|---|
| `libtflm.a` | `$TOOLCHAIN_STAGING/usr/lib/` |
| TFLM C++ headers (200+) | `$TOOLCHAIN_STAGING/usr/include/tflite-micro/` |
| `tflm-hello-world` (optional) | `/usr/bin/tflm-hello-world` on the device |

The library and headers are installed to the **staging area** (not the target filesystem root) so they
are available to other packages at build time. Only the optional `tflm-hello-world` binary is deployed
to the device filesystem.

## Linking Against libtflm.a

To use TFLM from another Freetz package, add the staging include and lib paths and declare a `select`
dependency:

```makefile
MY_PACKAGE_CXXFLAGS := -I$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/tflite-micro
MY_PACKAGE_CXXFLAGS += -std=c++17 -fno-rtti -fno-exceptions
MY_PACKAGE_LDFLAGS  := -L$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib -ltflm
```

```kconfig
# In your Config.in
select FREETZ_PACKAGE_TFLITE_MICRO
```

## Build Pipeline

The build involves three stages:

1. **Host tool installation** — numpy and Pillow are installed into freetz's own Python 3
   (`tools/path/python3`) using `python3 -m pip install`. These are required by the TFLM
   source-tree generator script.

2. **Source-tree generation** — the official `create_tflm_tree.py` script is run on the host
   to produce a flat, single-directory source tree (`tflm-tree/`) containing all required `.cc`
   and `.h` files, including third-party dependencies (kissfft, flatbuffers, ruy, gemmlowp).

3. **Cross-compilation** — every `.cc` file in the flat tree is compiled to MIPS32 with
   `$(TARGET_CC)` / `$(TARGET_CXX)`, then archived into `libtflm.a` with `$(TARGET_AR)`.

## Build Notes

- **Python 3 host tools**: freetz has its own Python 3.14 at `tools/path/python3` that shadows any
  system Python during the build. numpy and Pillow are automatically installed into this interpreter
  by the `.mk` recipe (idempotent — subsequent builds skip re-installation if already present).

- **`array.h` workaround**: the TFLM generator omits a transitive dependency (`array.h`) needed by
  `tensorflow/lite/micro/span.h`; the recipe copies it from the TFLM source tree into the generated
  flat tree automatically.

- **Kiss FFT include path**: the flat source tree places `kissfft` under `third_party/kissfft`; the
  cross-compilation step adds `-I$(TFLITE_MICRO_TREE_DIR)/third_party/kissfft` for correct header
  resolution.

- **Compiler flags**: all files are built with `-std=c++17 -fno-rtti -fno-exceptions -O2` — the same
  flags required by the upstream TFLM build system. Exceptions and RTTI are deliberately disabled to
  keep code size small and avoid uClibc compatibility issues.

- **Static linking only**: `libtflm.a` is a static archive; there is no shared library and no
  `lib*.so` is installed to the device.

## Relevant Files

| File | Purpose |
|---|---|
| [`make/pkgs/tflite-micro/tflite-micro.mk`](../../make/pkgs/tflite-micro/tflite-micro.mk) | Package makefile: download, tree generation, cross-compilation, staging install |
| [`make/pkgs/tflite-micro/Config.in`](../../make/pkgs/tflite-micro/Config.in) | Kconfig options: main package + optional hello_world demo |
| [`make/pkgs/tflite-micro/external.in`](../../make/pkgs/tflite-micro/external.in) | External (squashfs) configuration for the hello_world binary |
| [`make/pkgs/tflite-micro/external.files`](../../make/pkgs/tflite-micro/external.files) | List of files to externalize |
