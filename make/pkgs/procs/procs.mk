$(call PKG_INIT_BIN, 0.14.11)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.14.11.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(PROCS_VERSION).tar.gz
$(PKG)_HASH:=3d6b3561ce05362a092ea8488458f552d6636d3a280290e21f841c432cadf91a
$(PKG)_SITE:=https://github.com/dalance/procs/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/procs-v0.14.11
### WEBSITE:=https://github.com/dalance/procs
### CHANGES:=https://github.com/dalance/procs/releases
### CVSREPO:=https://github.com/dalance/procs

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
# procs builds without --locked
PROCS_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(PROCS_CARGO_BUILD_STD_FLAGS),cargo build --release)
PROCS_CARGO_HOME:=$(abspath $(PROCS_DIR)/.cargo)
$(PKG)_BINARY:=$(PROCS_DIR)/target/$(PROCS_RUST_TARGET_DIR)/release/procs
$(PKG)_TARGET_BINARY:=$(PROCS_DEST_DIR)/usr/bin/procs

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(PROCS_BINARY): $(PROCS_DIR)/.configured
	cd $(PROCS_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(PROCS_DIR))"; \
	export CARGO_HOME="$(PROCS_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(PROCS_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.3) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	$(call NIX_APPLY_UCLIBC_MIPS_PATCHES_026_SAFE__INT,0.26.4) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PROCS_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(PROCS_CARGO_BUILD_CMD) --target "$(PROCS_RUST_TARGET_ARG)" --bin procs

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(PROCS_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(PROCS_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(PROCS_DIR) clean
	$(RM) $(PROCS_BINARY) $(PROCS_DIR)/.configured $(PROCS_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(PROCS_TARGET_BINARY)

$(PKG_FINISH)
