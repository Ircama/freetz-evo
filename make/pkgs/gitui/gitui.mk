$(call PKG_INIT_BIN, 0.28.1)
include $(MAKE_DIR)/include/650-rust-cargo.mk
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
GITUI_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
GITUI_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(GITUI_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
GITUI_CARGO_HOME:=$(abspath $(GITUI_DIR)/.cargo)
$(PKG)_BINARY:=$(GITUI_DIR)/target/$(GITUI_RUST_TARGET_DIR)/release/gitui
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/gitui

$(PKG)_DEPENDS_ON += rust-host openssl
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(GITUI_DIR)/.configured
	cd $(GITUI_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(GITUI_DIR))"; \
	export CARGO_HOME="$(GITUI_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(GITUI_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.3) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.43) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call TUI_TEXTAREA_APPLY_ATOMICU64_FALLBACK__INT,0.7.0) \
	$(call GITUI_APPLY_ASYNCGIT_GENERATION_ATOMIC_PATCH__INT) \
	export OPENSSL_NO_VENDOR=1; \
	export OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"; \
	export OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"; \
	export OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(GITUI_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(GITUI_CARGO_BUILD_CMD) --target "$(GITUI_RUST_TARGET_ARG)" --bin gitui || CARGO_BUILD_JOBS=1 $(GITUI_CARGO_BUILD_CMD) --target "$(GITUI_RUST_TARGET_ARG)" --bin gitui

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(GITUI_DIR) clean
	$(RM) $($(PKG)_BINARY) $(GITUI_DIR)/.configured $(GITUI_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
