$(call PKG_INIT_BIN, 0.13.2)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.13.2.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f591972106d66b22184fe412327ca1419944e925914fc71c9c2e43528f081827
$(PKG)_SITE:=https://github.com/mrjackwills/oxker/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/oxker-v0.13.2
### WEBSITE:=https://github.com/mrjackwills/oxker
### CHANGES:=https://github.com/mrjackwills/oxker/releases
### CVSREPO:=https://github.com/mrjackwills/oxker

include $(MAKE_DIR)/include/650-rust-cargo.mk

OXKER_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
OXKER_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
OXKER_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
OXKER_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(OXKER_CARGO_BUILD_STD_FLAGS),cargo build --release)
OXKER_CARGO_HOME:=$(abspath $(OXKER_DIR)/.cargo)
$(PKG)_BINARY:=$(OXKER_DIR)/target/$(OXKER_RUST_TARGET_DIR)/release/oxker
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/oxker

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(OXKER_DIR)/.configured
	cd $(OXKER_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(OXKER_DIR))"; \
	export CARGO_HOME="$(OXKER_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo fetch --target "$(OXKER_RUST_TARGET_ARG)"; \
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
	done; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(OXKER_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(OXKER_CARGO_BUILD_CMD) --target "$(OXKER_RUST_TARGET_ARG)" --bin oxker

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(OXKER_DIR) clean
	$(RM) $($(PKG)_BINARY) $(OXKER_DIR)/.configured $(OXKER_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
