$(call PKG_INIT_BIN, 48.0.0)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE:=cryptography-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=cryptography-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/cryptography
$(PKG)_HASH:=5c3932f4436d1cccb036cb0eaef46e6e2db91035166f1ad6505c3c9d5a635920
### WEBSITE:=https://cryptography.io/
### MANPAGE:=https://cryptography.io/en/latest/
### CHANGES:=https://cryptography.io/en/latest/changelog/
### CVSREPO:=https://github.com/pyca/cryptography
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += openssl python3 python3-cffi python3-typing-extensions rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_CRYPTOGRAPHY
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_CRYPTOGRAPHY_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_CRYPTOGRAPHY_RUST_BUILD_STD:=std\,panic_abort
# Custom (non-builtin) targets like i686-unknown-linux-uclibc are provided as
# JSON spec files under toolchain/rust/targets/. maturin does NOT accept a .json
# path as target (it parses the string with target_lexicon and aborts with
# "Unknown target triple"), so CARGO_BUILD_TARGET must use the plain triple NAME
# and cargo/rustc resolve the spec via RUST_TARGET_PATH. On recent rustc
# (>= ~1.88) loading a custom target requires -Zunstable-options, which must be
# set in BOTH the cargo config.toml `rustflags` (maturin overrides the RUSTFLAGS
# env var with CARGO_ENCODED_RUSTFLAGS for the cargo build, but propagates
# config.toml rustflags) AND the RUSTFLAGS env var (cargo metadata's target-info
# rustc query uses ONLY env RUSTFLAGS and ignores config.toml rustflags).
# Additionally, the Rust `libc` crate ships no x86 (32-bit) uClibc module for
# ANY 0.2.x version, so on i686 the build-std libc must be patched with
# RUST_APPLY_UCLIBC_X86_LIBC_PATCH.
PYTHON3_CRYPTOGRAPHY_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR))
PYTHON3_CRYPTOGRAPHY_WORKDIR:=$(abspath $(PYTHON3_CRYPTOGRAPHY_DIR))
PYTHON3_CRYPTOGRAPHY_BUILD_PATH:=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH
PYTHON3_CRYPTOGRAPHY_CARGO_HOME:=$(PYTHON3_CRYPTOGRAPHY_WORKDIR)/.cargo
PYTHON3_CRYPTOGRAPHY_RUSTUP_HOME:=$(HOME)/.rustup
PYTHON3_CRYPTOGRAPHY_XDG_CACHE_HOME:=$(PYTHON3_CRYPTOGRAPHY_WORKDIR)/.cache

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# maturin rejects the generic 'python3' interpreter name; use versioned path
$($(PKG)_TARGET_BINARY): HOST_PYTHON3_BIN = $(HOST_TOOLS_DIR)/usr/bin/$(PYTHON)
$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd $(PYTHON3_CRYPTOGRAPHY_DIR); \
	export HOME="$(PYTHON3_CRYPTOGRAPHY_WORKDIR)"; \
	export CARGO_HOME="$(PYTHON3_CRYPTOGRAPHY_CARGO_HOME)"; \
	export RUSTUP_HOME="$(PYTHON3_CRYPTOGRAPHY_RUSTUP_HOME)"; \
	export XDG_CACHE_HOME="$(PYTHON3_CRYPTOGRAPHY_XDG_CACHE_HOME)"; \
	export PATH=$(PYTHON3_CRYPTOGRAPHY_BUILD_PATH); \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),rustflags = ["-Zunstable-options"]\n)' \
		"$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR)"; \
	mkdir -p "$$CARGO_HOME/pyo3-config"; \
	printf 'implementation=CPython\nversion=3.14\nshared=true\nabi3=true\nlib_name=python3.14\nld_version=3.14\npointer_width=32\nsuppress_build_script_link_lines=false\n' \
		> "$$CARGO_HOME/pyo3-config/config.ini"; \
	if ! grep -q 'PYO3_CROSS_INCLUDE_DIR' src/rust/cryptography-cffi/build.rs; then \
		python3 -c "content = open('src/rust/cryptography-cffi/build.rs').read(); old = '    for python_include in env::split_paths(&python_includes) {'; new = '    // freetz-ng cross-compile: add PYO3_CROSS_INCLUDE_DIR first\n    if let Some(cross_include) = std::env::var_os(\"PYO3_CROSS_INCLUDE_DIR\") {\n        if !cross_include.is_empty() {\n            build.include(cross_include);\n        }\n    }\n\n    for python_include in env::split_paths(&python_includes) {'; assert old in content, 'Pattern not found'; content = content.replace(old, new, 1); open('src/rust/cryptography-cffi/build.rs', 'w').write(content)"; \
	fi; \
	$(if $(PYTHON3_CRYPTOGRAPHY_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
	$(if $(PYTHON3_CRYPTOGRAPHY_NEEDS_X86_LIBC_PATCH),find "$(PYTHON3_CRYPTOGRAPHY_WORKDIR)/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	cd "$(FREETZ_BASE_DIR)"; \
	$(call Build/PyMod3/Pip, PYTHON3_CRYPTOGRAPHY, , \
		HOME="$(PYTHON3_CRYPTOGRAPHY_WORKDIR)" \
		CARGO_HOME="$(PYTHON3_CRYPTOGRAPHY_CARGO_HOME)" \
		RUSTUP_HOME="$(PYTHON3_CRYPTOGRAPHY_RUSTUP_HOME)" \
		XDG_CACHE_HOME="$(PYTHON3_CRYPTOGRAPHY_XDG_CACHE_HOME)" \
		PATH="$(PYTHON3_CRYPTOGRAPHY_BUILD_PATH)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR) -DLONG_BIT=(8*__SIZEOF_LONG__) -Wno-sign-conversion" \
		OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib" \
		OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		CARGO_BUILD_TARGET="$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR)" \
		RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD=$(PYTHON3_CRYPTOGRAPHY_RUST_BUILD_STD)) \
		RUSTFLAGS="$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zunstable-options )-C linker=$(TARGET_CROSS)gcc" \
		PYO3_CROSS_LIB_DIR="$(PYTHON3_STAGING_LIB_DIR)" \
		PYO3_CROSS_INCLUDE_DIR="$(PYTHON3_STAGING_INC_DIR)" \
		PYO3_CONFIG_FILE="$$CARGO_HOME/pyo3-config/config.ini" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/.configured
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/build
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography
	$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography-$(PYTHON3_CRYPTOGRAPHY_VERSION)*.dist-info

$(PKG_FINISH)
