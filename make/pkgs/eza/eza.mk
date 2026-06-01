$(call PKG_INIT_BIN, 0.23.4)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.23.4.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9fbcad518b8a2095206ac385329ca62d216bf9fdc652dde2d082fcb37c309635
$(PKG)_SITE:=https://github.com/eza-community/eza/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/eza-0.23.4
### WEBSITE:=https://github.com/eza-community/eza
### CHANGES:=https://github.com/eza-community/eza/releases
### CVSREPO:=https://github.com/eza-community/eza

EZA_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
EZA_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
EZA_RUST_ENV_TARGET:=$(subst -,_,$(EZA_RUST_TARGET_DIR))
EZA_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
EZA_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(EZA_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
$(PKG)_BINARY:=$(EZA_DIR)/target/$(EZA_RUST_TARGET_DIR)/release/eza
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/eza

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(EZA_DIR)/.configured
	cd $(EZA_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	cargo fetch --locked --target "$(EZA_RUST_TARGET_ARG)"; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(EZA_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml; \
	$(EZA_CARGO_BUILD_CMD) --target "$(EZA_RUST_TARGET_ARG)" --bin eza --no-default-features

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(EZA_DIR) clean
	$(RM) $($(PKG)_BINARY) $(EZA_DIR)/.configured $(EZA_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)