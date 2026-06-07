$(call PKG_INIT_BIN, 26.5.6)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v26.5.6.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=a18445df86a20068f7b17609d12d6f635de488958579ae7a2b143a244ba7e63f
$(PKG)_SITE:=https://github.com/sxyazi/yazi/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/yazi-v26.5.6
### WEBSITE:=https://github.com/sxyazi/yazi
### CHANGES:=https://github.com/sxyazi/yazi/releases
### CVSREPO:=https://github.com/sxyazi/yazi

include $(MAKE_DIR)/include/650-rust-cargo.mk

YAZI_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
YAZI_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
YAZI_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
YAZI_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(YAZI_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
YAZI_CARGO_HOME:=$(abspath $(YAZI_DIR)/.cargo)
$(PKG)_BINARY_YAZI:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/yazi
$(PKG)_BINARY_YA:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/ya
$(PKG)_TARGET_BINARY_YAZI:=$($(PKG)_DEST_DIR)/usr/bin/yazi
$(PKG)_TARGET_BINARY_YA:=$($(PKG)_DEST_DIR)/usr/bin/ya

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_YAZI) $($(PKG)_BINARY_YA): $(YAZI_DIR)/.configured
	cd $(YAZI_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(YAZI_DIR))"; \
	export CARGO_HOME="$(YAZI_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(YAZI_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(YAZI_CARGO_BUILD_CMD) --target "$(YAZI_RUST_TARGET_ARG)" --bin yazi --bin ya

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY_YAZI),/usr/bin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY_YA),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY_YAZI) $($(PKG)_TARGET_BINARY_YA)

$(pkg)-clean:
	-$(SUBMAKE) -C $(YAZI_DIR) clean
	$(RM) $($(PKG)_BINARY_YAZI) $($(PKG)_BINARY_YA) $(YAZI_DIR)/.configured $(YAZI_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY_YAZI) $($(PKG)_TARGET_BINARY_YA)

$(PKG_FINISH)
