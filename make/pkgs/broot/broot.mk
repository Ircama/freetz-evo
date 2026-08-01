$(call PKG_INIT_BIN, 1.56.4)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v1.56.4.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ec49422f335965ee0338cd630869eb1fc6d974d43648bd483c802fd7e9aea99b
$(PKG)_SITE:=https://github.com/Canop/broot/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/broot-v1.56.4
### WEBSITE:=https://github.com/Canop/broot
### CHANGES:=https://github.com/Canop/broot/releases
### CVSREPO:=https://github.com/Canop/broot

BROOT_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
BROOT_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
BROOT_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
BROOT_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(BROOT_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
BROOT_CARGO_HOME:=$(abspath $(BROOT_DIR)/.cargo)
$(PKG)_BINARY:=$(BROOT_DIR)/target/$(BROOT_RUST_TARGET_DIR)/release/broot
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/broot

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(BROOT_DIR)/.configured
	cd $(BROOT_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(BROOT_DIR))"; \
	export CARGO_HOME="$(BROOT_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	rustup toolchain list 2>&1 | grep -q nightly || rustup toolchain install nightly 2>&1; \
	rustup component add rust-src --toolchain nightly 2>&1; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(BROOT_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.2) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(BROOT_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(BROOT_CARGO_BUILD_CMD) --target "$(BROOT_RUST_TARGET_ARG)" --bin broot || CARGO_BUILD_JOBS=1 $(BROOT_CARGO_BUILD_CMD) --target "$(BROOT_RUST_TARGET_ARG)" --bin broot

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(BROOT_DIR) clean
	$(RM) $($(PKG)_BINARY) $(BROOT_DIR)/.configured $(BROOT_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
