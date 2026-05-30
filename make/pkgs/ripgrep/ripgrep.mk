$(call PKG_INIT_BIN, 15.1.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=046fa01a216793b8bd2750f9d68d4ad43986eb9c0d6122600f993906012972e8
$(PKG)_SITE:=https://github.com/BurntSushi/ripgrep/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/ripgrep-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/BurntSushi/ripgrep
### MANPAGE:=https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md
### CHANGES:=https://github.com/BurntSushi/ripgrep/releases
### CVSREPO:=https://github.com/BurntSushi/ripgrep

RIPGREP_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
RIPGREP_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
RIPGREP_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
RIPGREP_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(RIPGREP_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(RIPGREP_DIR)/target/$(RIPGREP_RUST_TARGET_DIR)/release/rg
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rg

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(RIPGREP_DIR)/.configured
	@echo "Building ripgrep with Cargo..."
	cd $(RIPGREP_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(RIPGREP_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(RIPGREP_CARGO_BUILD_CMD) --target "$(RIPGREP_RUST_TARGET_ARG)" --bin rg

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RIPGREP_DIR) clean
	$(RM) $($(PKG)_BINARY) $(RIPGREP_DIR)/.configured $(RIPGREP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
