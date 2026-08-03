$(call PKG_INIT_BIN, 3.11.9)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE:=orjson-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=orjson-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/o/orjson
$(PKG)_HASH:=4fef17e1f8722c11587a6ef18e35902450221da0028e65dbaaa543619e68e48f
### WEBSITE:=https://github.com/ijl/orjson
### CHANGES:=https://github.com/ijl/orjson/releases
### CVSREPO:=https://github.com/ijl/orjson
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_ORJSON
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_ORJSON_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_ORJSON_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_ORJSON_RUST_BUILD_STD:=std$(_comma)panic_abort
# Custom (non-builtin) targets (x86, aarch64, ...) must be passed to maturin by
# triple NAME (it cannot parse a .json path) and resolved via RUST_TARGET_PATH;
# loading them requires -Zunstable-options in both the cargo config.toml
# rustflags and the RUSTFLAGS env var (see python3-cryptography for details).
# i686 additionally needs the shared x86 uClibc libc module patch.
PYTHON3_ORJSON_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(PYTHON3_ORJSON_RUST_TARGET_DIR))

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/orjson/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

PYTHON3_ORJSON_WORKDIR:=$(abspath $(PYTHON3_ORJSON_DIR))
PYTHON3_ORJSON_CARGO_HOME:=$(PYTHON3_ORJSON_WORKDIR)/.cargo
PYTHON3_ORJSON_RUSTUP_HOME:=$(HOME)/.rustup
PYTHON3_ORJSON_XDG_CACHE_HOME:=$(PYTHON3_ORJSON_WORKDIR)/.cache

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd "$(PYTHON3_ORJSON_WORKDIR)" || exit 1; \
	export HOME="$(PYTHON3_ORJSON_WORKDIR)"; \
	export CARGO_HOME="$(PYTHON3_ORJSON_CARGO_HOME)"; \
	export RUSTUP_HOME="$(PYTHON3_ORJSON_RUSTUP_HOME)"; \
	export XDG_CACHE_HOME="$(PYTHON3_ORJSON_XDG_CACHE_HOME)"; \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$$PATH; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),rustflags = ["-Zunstable-options"]\n)' \
		"$(PYTHON3_ORJSON_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --manifest-path Cargo.toml --target "$(PYTHON3_ORJSON_RUST_TARGET_DIR)"; \
	$(if $(PYTHON3_ORJSON_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
	$(if $(PYTHON3_ORJSON_NEEDS_X86_LIBC_PATCH),find "$(PYTHON3_ORJSON_WORKDIR)/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	cd "$(FREETZ_BASE_DIR)"; \
	$(call Build/PyMod3/Pip, PYTHON3_ORJSON, , \
		HOME="$(PYTHON3_ORJSON_WORKDIR)" \
		CARGO_HOME="$(PYTHON3_ORJSON_CARGO_HOME)" \
		RUSTUP_HOME="$(PYTHON3_ORJSON_RUSTUP_HOME)" \
		XDG_CACHE_HOME="$(PYTHON3_ORJSON_XDG_CACHE_HOME)" \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
		CARGO_BUILD_TARGET="$(PYTHON3_ORJSON_RUST_TARGET_DIR)" \
		RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD="$(PYTHON3_ORJSON_RUST_BUILD_STD)") \
		RUSTFLAGS="$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zunstable-options )-C linker=$(TARGET_CROSS)gcc" \
		PYO3_CROSS_LIB_DIR="$(PYTHON3_STAGING_LIB_DIR)" \
		PYO3_CROSS_PYTHON_VERSION="$(PYTHON3_MAJOR_VERSION)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_ORJSON_DIR)/.configured
	$(RM) -r $(PYTHON3_ORJSON_DIR)/build
	$(RM) -r $(PYTHON3_ORJSON_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ORJSON_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/orjson \
		$(PYTHON3_ORJSON_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/orjson-*.dist-info

$(PKG_FINISH)