$(call PKG_INIT_BIN, 0.9.9)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.9.9.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(ZOXIDE_VERSION).tar.gz
$(PKG)_HASH:=eddc76e94db58567503a3893ecac77c572f427f3a4eabdfc762f6773abf12c63
$(PKG)_SITE:=https://github.com/ajeetdsouza/zoxide/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/zoxide-0.9.9
### WEBSITE:=https://github.com/ajeetdsouza/zoxide
### CHANGES:=https://github.com/ajeetdsouza/zoxide/releases
### CVSREPO:=https://github.com/ajeetdsouza/zoxide

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
ZOXIDE_CARGO_HOME:=$(abspath $(ZOXIDE_DIR)/.cargo)
$(PKG)_BINARY:=$(ZOXIDE_DIR)/target/$(ZOXIDE_RUST_TARGET_DIR)/release/zoxide
$(PKG)_TARGET_BINARY:=$(ZOXIDE_DEST_DIR)/usr/bin/zoxide

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(ZOXIDE_BINARY): $(ZOXIDE_DIR)/.configured
	cd $(ZOXIDE_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOME="$(abspath $(ZOXIDE_DIR))"; \
	export CARGO_HOME="$(ZOXIDE_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(ZOXIDE_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(ZOXIDE_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(ZOXIDE_CARGO_BUILD_CMD) --target "$(ZOXIDE_RUST_TARGET_ARG)" --bin zoxide

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(ZOXIDE_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(ZOXIDE_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ZOXIDE_DIR) clean
	$(RM) $(ZOXIDE_BINARY) $(ZOXIDE_DIR)/.configured $(ZOXIDE_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(ZOXIDE_TARGET_BINARY)

$(PKG_FINISH)