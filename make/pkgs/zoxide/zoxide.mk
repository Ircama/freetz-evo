$(call PKG_INIT_BIN, 0.9.9)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.9.9.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=eddc76e94db58567503a3893ecac77c572f427f3a4eabdfc762f6773abf12c63
$(PKG)_SITE:=https://github.com/ajeetdsouza/zoxide/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/zoxide-0.9.9
### WEBSITE:=https://github.com/ajeetdsouza/zoxide
### CHANGES:=https://github.com/ajeetdsouza/zoxide/releases
### CVSREPO:=https://github.com/ajeetdsouza/zoxide

ZOXIDE_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
ZOXIDE_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
ZOXIDE_RUST_ENV_TARGET:=$(subst -,_,$(ZOXIDE_RUST_TARGET_DIR))
ZOXIDE_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
ZOXIDE_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(ZOXIDE_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(ZOXIDE_DIR)/target/$(ZOXIDE_RUST_TARGET_DIR)/release/zoxide
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/zoxide

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(ZOXIDE_DIR)/.configured
	cd $(ZOXIDE_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(ZOXIDE_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	cargo fetch --locked --target "$(ZOXIDE_RUST_TARGET_ARG)"; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(ZOXIDE_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(ZOXIDE_CARGO_BUILD_CMD) --target "$(ZOXIDE_RUST_TARGET_ARG)" --bin zoxide

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ZOXIDE_DIR) clean
	$(RM) $($(PKG)_BINARY) $(ZOXIDE_DIR)/.configured $(ZOXIDE_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)