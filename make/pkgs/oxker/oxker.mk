$(call PKG_INIT_BIN, 0.13.2)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.13.2.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(OXKER_VERSION).tar.gz
$(PKG)_HASH:=f591972106d66b22184fe412327ca1419944e925914fc71c9c2e43528f081827
$(PKG)_SITE:=https://github.com/mrjackwills/oxker/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/oxker-v0.13.2
### WEBSITE:=https://github.com/mrjackwills/oxker
### CHANGES:=https://github.com/mrjackwills/oxker/releases
### CVSREPO:=https://github.com/mrjackwills/oxker

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
# oxker builds without --locked
OXKER_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(OXKER_CARGO_BUILD_STD_FLAGS),cargo build --release)
OXKER_CARGO_HOME:=$(abspath $(OXKER_DIR)/.cargo)
$(PKG)_BINARY:=$(OXKER_DIR)/target/$(OXKER_RUST_TARGET_DIR)/release/oxker
$(PKG)_TARGET_BINARY:=$(OXKER_DEST_DIR)/usr/bin/oxker

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(OXKER_BINARY): $(OXKER_DIR)/.configured
	cd $(OXKER_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(OXKER_DIR))"; \
	export CARGO_HOME="$(OXKER_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(OXKER_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call SOCKET2_APPLY_UCLIBC_IPV6_TRANSPARENT_PATCH__INT) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(OXKER_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(OXKER_CARGO_BUILD_CMD) --target "$(OXKER_RUST_TARGET_ARG)" --bin oxker

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(OXKER_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(OXKER_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(OXKER_DIR) clean
	$(RM) $(OXKER_BINARY) $(OXKER_DIR)/.configured $(OXKER_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(OXKER_TARGET_BINARY)

$(PKG_FINISH)
