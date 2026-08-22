$(call PKG_INIT_BIN, 0.23.1)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.23.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(BANDWHICH_VERSION).tar.gz
$(PKG)_HASH:=aafb96d059cf9734da915dca4f5940c319d2e6b54e2ffb884332e9f5e820e6d7
$(PKG)_SITE:=https://github.com/imsnif/bandwhich/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/bandwhich-v0.23.1
### WEBSITE:=https://github.com/imsnif/bandwhich
### CHANGES:=https://github.com/imsnif/bandwhich/releases
### CVSREPO:=https://github.com/imsnif/bandwhich

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
BANDWHICH_CARGO_HOME:=$(abspath $(BANDWHICH_DIR)/.cargo)
$(PKG)_BINARY:=$(BANDWHICH_DIR)/target/$(BANDWHICH_RUST_TARGET_DIR)/release/bandwhich
$(PKG)_TARGET_BINARY:=$(BANDWHICH_DEST_DIR)/usr/bin/bandwhich

$(eval $(call RUST_DEPENDS_VARS))
$(PKG)_DEPENDS_ON += libpcap

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(BANDWHICH_BINARY): $(BANDWHICH_DIR)/.configured
	cd $(BANDWHICH_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(BANDWHICH_DIR))"; \
	export CARGO_HOME="$(BANDWHICH_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(BANDWHICH_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.37) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(BANDWHICH_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(BANDWHICH_CARGO_BUILD_CMD) --target "$(BANDWHICH_RUST_TARGET_ARG)" --bin bandwhich || CARGO_BUILD_JOBS=1 $(BANDWHICH_CARGO_BUILD_CMD) --target "$(BANDWHICH_RUST_TARGET_ARG)" --bin bandwhich

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(BANDWHICH_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(BANDWHICH_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(BANDWHICH_DIR) clean
	$(RM) $(BANDWHICH_BINARY) $(BANDWHICH_DIR)/.configured $(BANDWHICH_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(BANDWHICH_TARGET_BINARY)

$(PKG_FINISH)
