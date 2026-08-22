$(call PKG_INIT_BIN, 0.9.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=0.9.0.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(TAC_VERSION).tar.gz
$(PKG)_HASH:=dafe0126ee4ed55c7cd60c6b559f43724a74751deed3c1b078f4f510311acab2
$(PKG)_SITE:=https://github.com/uutils/coreutils/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/tac-coreutils-0.9.0
### WEBSITE:=https://github.com/uutils/coreutils
### CHANGES:=https://github.com/uutils/coreutils/releases
### CVSREPO:=https://github.com/uutils/coreutils

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
TAC_CARGO_HOME:=$(abspath $(TAC_DIR)/.cargo)
$(PKG)_BINARY:=$(TAC_DIR)/target/$(TAC_RUST_TARGET_DIR)/release/coreutils
$(PKG)_TARGET_BINARY:=$(TAC_DEST_DIR)/usr/bin/tac

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(TAC_BINARY): $(TAC_DIR)/.configured
	cd $(TAC_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(TAC_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(TAC_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(TAC_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(TAC_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOME="$(abspath $(TAC_DIR))"; \
	export CARGO_HOME="$(TAC_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(TAC_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(TAC_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(TAC_CARGO_BUILD_CMD) --target "$(TAC_RUST_TARGET_ARG)" --bin coreutils --no-default-features --features tac

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(TAC_BINARY),/usr/bin,,tac))

$(pkg):

$(pkg)-precompiled: $(TAC_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(TAC_DIR) clean
	$(RM) $(TAC_BINARY) $(TAC_DIR)/.configured $(TAC_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(TAC_TARGET_BINARY)

$(PKG_FINISH)