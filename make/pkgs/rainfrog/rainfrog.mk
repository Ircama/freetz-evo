$(call PKG_INIT_BIN, 0.3.18)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.3.18.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=3854293991b0dac036d640a7194be7fd71440c1e8739ffad39bab8dc651c8ade
$(PKG)_SITE:=https://github.com/achristmascarl/rainfrog/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/rainfrog-v0.3.18
### WEBSITE:=https://github.com/achristmascarl/rainfrog
### CHANGES:=https://github.com/achristmascarl/rainfrog/releases
### CVSREPO:=https://github.com/achristmascarl/rainfrog

RAINFROG_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
RAINFROG_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
RAINFROG_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
RAINFROG_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(RAINFROG_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(RAINFROG_DIR)/target/$(RAINFROG_RUST_TARGET_DIR)/release/rainfrog
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rainfrog

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(RAINFROG_DIR)/.configured
	cd $(RAINFROG_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(RAINFROG_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(RAINFROG_CARGO_BUILD_CMD) --target "$(RAINFROG_RUST_TARGET_ARG)" --bin rainfrog

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RAINFROG_DIR) clean
	$(RM) $($(PKG)_BINARY) $(RAINFROG_DIR)/.configured $(RAINFROG_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
