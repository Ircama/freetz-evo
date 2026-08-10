$(call PKG_INIT_BIN, 0.9.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=0.9.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=dafe0126ee4ed55c7cd60c6b559f43724a74751deed3c1b078f4f510311acab2
$(PKG)_SITE:=https://github.com/uutils/coreutils/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/sha256sum-coreutils-0.9.0
### WEBSITE:=https://github.com/uutils/coreutils
### CHANGES:=https://github.com/uutils/coreutils/releases
### CVSREPO:=https://github.com/uutils/coreutils

SHA256SUM_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
SHA256SUM_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
SHA256SUM_RUST_ENV_TARGET:=$(subst -,_,$(SHA256SUM_RUST_TARGET_DIR))
SHA256SUM_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
SHA256SUM_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(SHA256SUM_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
SHA256SUM_CARGO_HOME:=$(abspath $(SHA256SUM_DIR)/.cargo)
$(PKG)_BINARY:=$(SHA256SUM_DIR)/target/$(SHA256SUM_RUST_TARGET_DIR)/release/coreutils
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/sha256sum

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(SHA256SUM_DIR)/.configured
	cd $(SHA256SUM_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(SHA256SUM_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(SHA256SUM_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(SHA256SUM_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(SHA256SUM_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOME="$(abspath $(SHA256SUM_DIR))"; \
	export CARGO_HOME="$(SHA256SUM_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(SHA256SUM_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(SHA256SUM_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(SHA256SUM_CARGO_BUILD_CMD) --target "$(SHA256SUM_RUST_TARGET_ARG)" --bin coreutils --no-default-features --features sha256sum

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin,,sha256sum))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(SHA256SUM_DIR) clean
	$(RM) $($(PKG)_BINARY) $(SHA256SUM_DIR)/.configured $(SHA256SUM_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)