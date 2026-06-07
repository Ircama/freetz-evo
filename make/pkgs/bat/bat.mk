$(call PKG_INIT_BIN, 0.26.1)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.26.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4474de87e084953eefc1120cf905a79f72bbbf85091e30cf37c9214eafcaa9c9
$(PKG)_SITE:=https://github.com/sharkdp/bat/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/bat-0.26.1
### WEBSITE:=https://github.com/sharkdp/bat
### CHANGES:=https://github.com/sharkdp/bat/releases
### CVSREPO:=https://github.com/sharkdp/bat

BAT_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
BAT_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
BAT_RUST_ENV_TARGET:=$(subst -,_,$(BAT_RUST_TARGET_DIR))
BAT_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
BAT_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(BAT_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
BAT_CARGO_HOME:=$(abspath $(BAT_DIR)/.cargo)
$(PKG)_BINARY:=$(BAT_DIR)/target/$(BAT_RUST_TARGET_DIR)/release/bat
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/bat

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(BAT_DIR)/.configured
	cd $(BAT_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(BAT_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(BAT_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(BAT_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(BAT_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOME="$(abspath $(BAT_DIR))"; \
	export CARGO_HOME="$(BAT_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(BAT_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo fetch --locked --target "$(BAT_RUST_TARGET_ARG)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.43) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.3) \
	$(BAT_CARGO_BUILD_CMD) --target "$(BAT_RUST_TARGET_ARG)" --bin bat

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(BAT_DIR) clean
	$(RM) $($(PKG)_BINARY) $(BAT_DIR)/.configured $(BAT_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)