$(call PKG_INIT_BIN, 0.12.3)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=0.12.3.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(BOTTOM_VERSION).tar.gz
$(PKG)_HASH:=1c70894f0eceb7034075959ff3080cf4706c11d7c012912c24e777abe4e62b70
$(PKG)_SITE:=https://github.com/ClementTsang/bottom/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/bottom-0.12.3
### WEBSITE:=https://github.com/ClementTsang/bottom
### CHANGES:=https://github.com/ClementTsang/bottom/releases
### CVSREPO:=https://github.com/ClementTsang/bottom

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
BOTTOM_CARGO_HOME:=$(abspath $(BOTTOM_DIR)/.cargo)
$(PKG)_BINARY:=$(BOTTOM_DIR)/target/$(BOTTOM_RUST_TARGET_DIR)/release/btm
$(PKG)_TARGET_BINARY:=$(BOTTOM_DEST_DIR)/usr/bin/btm

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(BOTTOM_BINARY): $(BOTTOM_DIR)/.configured
	cd $(BOTTOM_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(BOTTOM_DIR))"; \
	export CARGO_HOME="$(BOTTOM_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(BOTTOM_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.3) \
	$(call NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT,0.30.1) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(BOTTOM_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(BOTTOM_CARGO_BUILD_CMD) --target "$(BOTTOM_RUST_TARGET_ARG)" --bin btm || CARGO_BUILD_JOBS=1 $(BOTTOM_CARGO_BUILD_CMD) --target "$(BOTTOM_RUST_TARGET_ARG)" --bin btm

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(BOTTOM_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(BOTTOM_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(BOTTOM_DIR) clean
	$(RM) $(BOTTOM_BINARY) $(BOTTOM_DIR)/.configured $(BOTTOM_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(BOTTOM_TARGET_BINARY)

$(PKG_FINISH)
