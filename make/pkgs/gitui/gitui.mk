$(call PKG_INIT_BIN, 0.28.1)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.28.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=0400cbf59605490b5fb8779f9af41fa4d7a1bb748093ca0e13156a5dff31c7aa
$(PKG)_SITE:=https://github.com/extrawurst/gitui/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/gitui-v0.28.1
### WEBSITE:=https://github.com/extrawurst/gitui
### CHANGES:=https://github.com/extrawurst/gitui/releases
### CVSREPO:=https://github.com/extrawurst/gitui

GITUI_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
GITUI_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
GITUI_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
GITUI_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(GITUI_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(GITUI_DIR)/target/$(GITUI_RUST_TARGET_DIR)/release/gitui
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/gitui

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(GITUI_DIR)/.configured
	cd $(GITUI_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(GITUI_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(GITUI_CARGO_BUILD_CMD) --target "$(GITUI_RUST_TARGET_ARG)" --bin gitui

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(GITUI_DIR) clean
	$(RM) $($(PKG)_BINARY) $(GITUI_DIR)/.configured $(GITUI_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
