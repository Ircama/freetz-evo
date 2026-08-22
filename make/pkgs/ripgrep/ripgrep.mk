$(call PKG_INIT_BIN, 15.1.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$(RIPGREP_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$(RIPGREP_VERSION).tar.gz
$(PKG)_HASH:=046fa01a216793b8bd2750f9d68d4ad43986eb9c0d6122600f993906012972e8
$(PKG)_SITE:=https://github.com/BurntSushi/ripgrep/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/ripgrep-$(RIPGREP_VERSION)
### WEBSITE:=https://github.com/BurntSushi/ripgrep
### MANPAGE:=https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md
### CHANGES:=https://github.com/BurntSushi/ripgrep/releases
### CVSREPO:=https://github.com/BurntSushi/ripgrep

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
RIPGREP_CARGO_HOME:=$(abspath $(RIPGREP_DIR)/.cargo)
# Custom (non-builtin) targets (x86, aarch64, ...) need the shared uClibc libc
# module patches: libc ships uclibc support for mips/arm but NOT x86 (missing
# sigset_t/sem_t etc. -> 284 E0425 errors) nor aarch64 (unsupported_target).
# See python3-cryptography and RUST_APPLY_UCLIBC_X86_LIBC_PATCH for details.
RIPGREP_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(RIPGREP_RUST_TARGET_DIR))
RIPGREP_NEEDS_AARCH64_LIBC_PATCH:=$(filter aarch64-unknown-linux-uclibc,$(RIPGREP_RUST_TARGET_DIR))
$(PKG)_BINARY:=$(RIPGREP_DIR)/target/$(RIPGREP_RUST_TARGET_DIR)/release/rg
$(PKG)_TARGET_BINARY:=$(RIPGREP_DEST_DIR)/usr/bin/rg

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(RIPGREP_BINARY): $(RIPGREP_DIR)/.configured
	@echo "Building ripgrep with Cargo..."
	cd $(RIPGREP_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(RIPGREP_DIR))"; \
	export CARGO_HOME="$(RIPGREP_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),rustflags = ["-Zunstable-options"]\n)' \
		"$(RIPGREP_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(RIPGREP_RUST_TARGET_DIR)"; \
	$(if $(RIPGREP_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
	$(if $(RIPGREP_NEEDS_X86_LIBC_PATCH),find "$(abspath $(RIPGREP_DIR))/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	$(if $(RIPGREP_NEEDS_AARCH64_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH)) \
	$(if $(RIPGREP_NEEDS_AARCH64_LIBC_PATCH),find "$(abspath $(RIPGREP_DIR))/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	$(RIPGREP_CARGO_BUILD_CMD) --target "$(RIPGREP_RUST_TARGET_ARG)" --bin rg

$(RIPGREP_TARGET_BINARY): $(RIPGREP_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $(RIPGREP_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RIPGREP_DIR) clean
	$(RM) $(RIPGREP_BINARY) $(RIPGREP_DIR)/.configured $(RIPGREP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(RIPGREP_TARGET_BINARY)

$(PKG_FINISH)
