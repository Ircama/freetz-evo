$(call PKG_INIT_BIN, 0.9.0)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.9.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=43527a78ba2e5e43a7ebd8d0da8b5af17a72455c5f88b4d1134f34908a594239
$(PKG)_SITE:=https://github.com/PaulJuliusMartinez/jless/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/jless-v0.9.0
### WEBSITE:=https://github.com/PaulJuliusMartinez/jless
### CHANGES:=https://github.com/PaulJuliusMartinez/jless/releases
### CVSREPO:=https://github.com/PaulJuliusMartinez/jless

LNAV_RS_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
LNAV_RS_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
LNAV_RS_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
LNAV_RS_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(LNAV_RS_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(LNAV_RS_DIR)/target/$(LNAV_RS_RUST_TARGET_DIR)/release/jless
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lnav-rs

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(LNAV_RS_DIR)/.configured
	cd $(LNAV_RS_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(LNAV_RS_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(LNAV_RS_CARGO_BUILD_CMD) --target "$(LNAV_RS_RUST_TARGET_ARG)" --bin jless

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	mkdir -p $(dir $@)
	cp $< $@
	$(TARGET_STRIP) $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LNAV_RS_DIR) clean
	$(RM) $($(PKG)_BINARY) $(LNAV_RS_DIR)/.configured $(LNAV_RS_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
