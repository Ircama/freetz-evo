# Commit that matches tag b8575 (2026-03-28)
LLAMA_CPP_COMMIT := 65097181e4c8358e7b570b48a2ae7b759f12bf26

$(call PKG_INIT_BIN, b8575)
$(PKG)_SOURCE_DOWNLOAD_NAME  := $(LLAMA_CPP_COMMIT).tar.gz
$(PKG)_SOURCE                := $(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH                  := 364aa2601fc6893a5ea19b822d2b012161c4ea78deea3328a8e5cc71b284443f
$(PKG)_SITE                  := https://github.com/ggml-org/llama.cpp/archive
$(PKG)_TARBALL_STRIP_COMPONENTS := 1
### VERSION:=b8575
### WEBSITE:=https://github.com/ggml-org/llama.cpp
### CHANGES:=https://github.com/ggml-org/llama.cpp/releases
### CVSREPO:=https://github.com/ggml-org/llama.cpp
### STEWARD:=Ircama

# --------------------------------------------------------------------------
# Eagerly-evaluated paths (avoid late-expansion bugs)
# --------------------------------------------------------------------------
LLAMA_CPP_BINDIR              := $(LLAMA_CPP_DIR)/bin
LLAMA_CPP_DEST_BINDIR         := $(LLAMA_CPP_DEST_DIR)/usr/bin
LLAMA_CPP_DEST_LIBDIR         := $(LLAMA_CPP_DEST_DIR)/usr/lib

# --------------------------------------------------------------------------
# All tools produced by LLAMA_BUILD_TOOLS=ON; used for exclusion logic
# --------------------------------------------------------------------------
LLAMA_CPP_TOOLS_ALL := \
	llama-batched-bench \
	llama-bench \
	llama-cli \
	llama-completion \
	llama-cvector-generator \
	llama-export-lora \
	llama-fit-params \
	llama-gguf-split \
	llama-imatrix \
	llama-mtmd-cli \
	llama-parser \
	llama-perplexity \
	llama-quantize \
	llama-rpc-server \
	llama-server \
	llama-tokenize \
	llama-tts

# Tools always included
LLAMA_CPP_TOOLS_DEFAULT := llama-cli llama-server llama-quantize

# Optional tools: each driven by its own FREETZ_… suboption
LLAMA_CPP_TOOLS_OPTIONAL := \
	llama-bench \
	llama-perplexity \
	llama-tokenize \
	llama-imatrix \
	llama-gguf-split \
	llama-batched-bench \
	llama-tts \
	llama-mtmd-cli

# Compute final tool list
LLAMA_CPP_TOOLS_SELECTED := $(LLAMA_CPP_TOOLS_DEFAULT) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_BENCH),llama-bench) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_PERPLEXITY),llama-perplexity) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_TOKENIZE),llama-tokenize) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_IMATRIX),llama-imatrix) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_GGUF_SPLIT),llama-gguf-split) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_BATCHED_BENCH),llama-batched-bench) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_TTS),llama-tts) \
	$(if $(FREETZ_PACKAGE_LLAMA_CPP_TOOL_MTMD),llama-mtmd-cli)

# Exclude everything not selected
$(PKG)_EXCLUDED += \
	$(patsubst %,$(LLAMA_CPP_DEST_BINDIR)/%,\
		$(filter-out $(LLAMA_CPP_TOOLS_SELECTED),$(LLAMA_CPP_TOOLS_ALL)))

# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------
$(PKG)_DEPENDS_ON += cmake-host

ifeq ($(strip $(FREETZ_PACKAGE_LLAMA_CPP_SERVER_OPENSSL)),y)
$(PKG)_DEPENDS_ON += openssl
endif

# Rebuild when relevant suboptions change
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_LLAMA_CPP_SERVER_OPENSSL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_LLAMA_CPP_SERVER_WEBUI

# --------------------------------------------------------------------------
# CMake cross-compile settings
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON

# Explicit cross-compiler (belt-and-suspenders alongside CC/CXX env vars)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_C_COMPILER="$(TARGET_CC)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CXX_COMPILER="$(TARGET_CXX)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_AR="$(TARGET_AR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_STRIP="$(TARGET_STRIP)"

# ARM (ARMv7/Cortex-A9): the llamafile SGEMM backend (sgemm.cpp) uses
# vcvt_f32_f16 which is an always_inline intrinsic requiring -mfpu=neon-fp16
# or higher. Whether the FP16 VFP extension is present at runtime on the
# target SoC cannot be guaranteed, so disable the entire llamafile backend
# on ARM to avoid both the compile error and potential illegal-instruction
# crashes. ggml falls back to its own SGEMM implementation.
ifeq ($(strip $(FREETZ_TARGET_ARCH_ARM)),y)
$(PKG)_CONFIGURE_OPTIONS += -DGGML_LLAMAFILE=OFF
endif

# Target system
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_PROCESSOR=$(FREETZ_TARGET_ARCH)

# Point cmake's find_* to the staging sysroot (not the host)
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH="$(TARGET_TOOLCHAIN_STAGING_DIR)"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY

# Install prefix
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX=/usr

# --------------------------------------------------------------------------
# Disable ALL GPU/accelerator backends (CPU-only build)
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += -DGGML_CUDA=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_METAL=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_VULKAN=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_OPENCL=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_SYCL=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_CANN=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_RPC=OFF
$(PKG)_CONFIGURE_OPTIONS += -DGGML_BLAS=OFF

# CRITICAL: disable -march=native for cross-compilation
$(PKG)_CONFIGURE_OPTIONS += -DGGML_NATIVE=OFF

# Misc host-tool avoidance
$(PKG)_CONFIGURE_OPTIONS += -DGGML_CCACHE=OFF

# --------------------------------------------------------------------------
# Build selection: tools only; no tests or playground examples
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_BUILD_COMMON=ON
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_BUILD_TOOLS=ON
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_BUILD_EXAMPLES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_BUILD_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_TOOLS_INSTALL=ON

# Embedded web UI for llama-server (adds ~2 MB to the binary, default OFF)
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_BUILD_WEBUI=$(if $(FREETZ_PACKAGE_LLAMA_CPP_SERVER_WEBUI),ON,OFF)

# OpenSSL for HTTPS support in llama-server (optional)
$(PKG)_CONFIGURE_OPTIONS += -DLLAMA_OPENSSL=$(if $(FREETZ_PACKAGE_LLAMA_CPP_SERVER_OPENSSL),ON,OFF)
ifeq ($(strip $(FREETZ_PACKAGE_LLAMA_CPP_SERVER_OPENSSL)),y)
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_SSL_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libssl.so"
$(PKG)_CONFIGURE_OPTIONS += -DOPENSSL_CRYPTO_LIBRARY="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libcrypto.so"
endif

# --------------------------------------------------------------------------
# Silence installer warnings about missing components (ggml installs its
# own targets; cmake --install reports "missing" if any component is absent)
# --------------------------------------------------------------------------
$(PKG)_CONFIGURE_OPTIONS += $(QUIETCMAKE)

# --------------------------------------------------------------------------
# Standard freetz cmake pipeline
# --------------------------------------------------------------------------
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

# Build step
$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LLAMA_CPP_DIR)
	@touch $@

# Install to DEST_DIR using cmake's install mechanism (strips via cmake --install)
$($(PKG)_DIR)/.installed: $($(PKG)_DIR)/.compiled
	$(MAKE_ENV) DESTDIR=$(LLAMA_CPP_DEST_DIR) \
		$(MAKE) -C $(LLAMA_CPP_DIR) install
	# Strip all installed ELF files (cmake install with --strip flag does
	# host-strip; we need the target cross-strip)
	find $(LLAMA_CPP_DEST_DIR)/usr/bin/ -maxdepth 1 -type f -executable \
		-exec $(TARGET_STRIP) --strip-unneeded {} \; 2>/dev/null || true
	find $(LLAMA_CPP_DEST_DIR)/usr/lib/ -maxdepth 1 \( -name "*.so*" \) \
		-exec $(TARGET_STRIP) --strip-unneeded {} \; 2>/dev/null || true
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.installed

# --------------------------------------------------------------------------
$(pkg)-clean:
	-$(SUBMAKE) -C $(LLAMA_CPP_DIR) clean
	$(RM) $(LLAMA_CPP_DIR)/.configured $(LLAMA_CPP_DIR)/.compiled \
	      $(LLAMA_CPP_DIR)/.installed

$(pkg)-uninstall:
	$(RM) -r $(LLAMA_CPP_DEST_BINDIR)/llama-* $(LLAMA_CPP_DEST_LIBDIR)/libllama* \
	         $(LLAMA_CPP_DEST_LIBDIR)/libggml*

$(PKG_FINISH)
