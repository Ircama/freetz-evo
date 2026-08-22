$(call PKG_INIT_BIN, 0.26.1)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.26.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(BAT_VERSION).tar.gz
$(PKG)_HASH:=4474de87e084953eefc1120cf905a79f72bbbf85091e30cf37c9214eafcaa9c9
$(PKG)_SITE:=https://github.com/sharkdp/bat/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/bat-0.26.1
### WEBSITE:=https://github.com/sharkdp/bat
### CHANGES:=https://github.com/sharkdp/bat/releases
### CVSREPO:=https://github.com/sharkdp/bat

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
BAT_CARGO_HOME:=$(abspath $(BAT_DIR)/.cargo)
$(PKG)_BINARY:=$(BAT_DIR)/target/$(BAT_RUST_TARGET_DIR)/release/bat
$(PKG)_TARGET_BINARY:=$(BAT_DEST_DIR)/usr/bin/bat

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(BAT_BINARY): $(BAT_DIR)/.configured
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
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(BAT_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.43) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.3) \
	$(BAT_CARGO_BUILD_CMD) --target "$(BAT_RUST_TARGET_ARG)" --bin bat

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(BAT_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(BAT_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(BAT_DIR) clean
	$(RM) $(BAT_BINARY) $(BAT_DIR)/.configured $(BAT_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(BAT_TARGET_BINARY)

$(PKG_FINISH)