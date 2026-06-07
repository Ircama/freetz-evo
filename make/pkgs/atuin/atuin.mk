$(call PKG_INIT_BIN, 18.16.1)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v18.16.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=752802d4e8eef4896e9bc779b82f85e3d433c5934df5169e9b0f2537acf7f6e9
$(PKG)_SITE:=https://github.com/atuinsh/atuin/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/atuin-v18.16.1
### WEBSITE:=https://github.com/atuinsh/atuin
### CHANGES:=https://github.com/atuinsh/atuin/releases
### CVSREPO:=https://github.com/atuinsh/atuin

ATUIN_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
ATUIN_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
ATUIN_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
ATUIN_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(ATUIN_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
ATUIN_CARGO_HOME:=$(abspath $(ATUIN_DIR)/.cargo)
$(PKG)_BINARY:=$(ATUIN_DIR)/target/$(ATUIN_RUST_TARGET_DIR)/release/atuin
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/atuin

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(ATUIN_DIR)/.configured
	cd $(ATUIN_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(ATUIN_DIR))"; \
	export CARGO_HOME="$(ATUIN_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo fetch --locked --target "$(ATUIN_RUST_TARGET_ARG)"; \
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
	done; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(ATUIN_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin || CARGO_BUILD_JOBS=1 $(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ATUIN_DIR) clean
	$(RM) $($(PKG)_BINARY) $(ATUIN_DIR)/.configured $(ATUIN_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
