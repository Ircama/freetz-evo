$(call PKG_INIT_BIN, 1.0.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v1.0.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=c07e2b82cb1cc327d977548e24d27fbbda8ee0cc4f2c3df9fb1b90c6e971e568
$(PKG)_SITE:=https://github.com/veeso/termscp/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/termscp-v1.0.0
### WEBSITE:=https://github.com/veeso/termscp
### CHANGES:=https://github.com/veeso/termscp/releases
### CVSREPO:=https://github.com/veeso/termscp

TERMSCP_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
TERMSCP_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
TERMSCP_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
TERMSCP_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(TERMSCP_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(TERMSCP_DIR)/target/$(TERMSCP_RUST_TARGET_DIR)/release/termscp
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/termscp

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(TERMSCP_DIR)/.configured
	cd $(TERMSCP_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(TERMSCP_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(TERMSCP_CARGO_BUILD_CMD) --target "$(TERMSCP_RUST_TARGET_ARG)" --bin termscp

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TERMSCP_DIR) clean
	$(RM) $($(PKG)_BINARY) $(TERMSCP_DIR)/.configured $(TERMSCP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
