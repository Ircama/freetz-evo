$(call PKG_INIT_BIN, 15.1.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58" in Config.in (fails on 0.9.x/1.0.14).
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=046fa01a216793b8bd2750f9d68d4ad43986eb9c0d6122600f993906012972e8
$(PKG)_SITE:=https://github.com/BurntSushi/ripgrep/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/ripgrep-$($(PKG)_VERSION)
### WEBSITE:=https://github.com/BurntSushi/ripgrep
### MANPAGE:=https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md
### CHANGES:=https://github.com/BurntSushi/ripgrep/releases
### CVSREPO:=https://github.com/BurntSushi/ripgrep

include $(MAKE_DIR)/include/650-rust-cargo.mk

RIPGREP_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
RIPGREP_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
RIPGREP_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
RIPGREP_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(RIPGREP_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
RIPGREP_CARGO_HOME:=$(abspath $(RIPGREP_DIR)/.cargo)
# Custom (non-builtin) targets (x86, aarch64, ...) need the shared x86 uClibc
# libc module patch: libc ships uclibc support for mips/arm but NOT x86
# (missing sigset_t/sem_t etc. -> 284 E0425 errors). See python3-cryptography
# and RUST_APPLY_UCLIBC_X86_LIBC_PATCH for details.
RIPGREP_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(RIPGREP_RUST_TARGET_DIR))
$(PKG)_BINARY:=$(RIPGREP_DIR)/target/$(RIPGREP_RUST_TARGET_DIR)/release/rg
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rg

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(RIPGREP_DIR)/.configured
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
	$(RIPGREP_CARGO_BUILD_CMD) --target "$(RIPGREP_RUST_TARGET_ARG)" --bin rg

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RIPGREP_DIR) clean
	$(RM) $($(PKG)_BINARY) $(RIPGREP_DIR)/.configured $(RIPGREP_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
