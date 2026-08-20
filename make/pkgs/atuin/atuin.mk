$(call PKG_INIT_BIN, 18.16.1)

# atuin 18.16.1 requires a recent toolchain: the Rust/Cargo cross-build
# fails on the old GCC/uClibc toolchains (0.9.x, 1.0.14). The option is
# therefore gated by "depends on FREETZ_TARGET_UCLIBC_1_0_58_MIN" in
# Config.in, which disables it on older toolchains.

include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v18.16.1.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=752802d4e8eef4896e9bc779b82f85e3d433c5934df5169e9b0f2537acf7f6e9
$(PKG)_SITE:=https://github.com/atuinsh/atuin/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/atuin-v18.16.1
### WEBSITE:=https://github.com/atuinsh/atuin
### CHANGES:=https://github.com/atuinsh/atuin/releases
### CVSREPO:=https://github.com/atuinsh/atuin

ATUIN_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
ATUIN_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
ATUIN_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
ATUIN_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(ATUIN_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
ATUIN_CARGO_HOME:=$(abspath $(ATUIN_DIR)/.cargo)
$(PKG)_BINARY:=$(ATUIN_DIR)/target/$(ATUIN_RUST_TARGET_DIR)/release/atuin
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/atuin

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(ATUIN_DIR)/.configured
	cd $(ATUIN_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(ATUIN_DIR))"; \
	export CARGO_HOME="$(ATUIN_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	rustup toolchain list 2>&1 | grep -q nightly || rustup toolchain install nightly 2>&1; \
	rustup component add rust-src --toolchain nightly 2>&1; \
	export XDG_CACHE_HOME="$(abspath $(ATUIN_DIR))/.cache"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie -C link-arg=-latomic"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-C", "link-arg=-latomic"]\n' \
		"$(ATUIN_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --locked --target "$(ATUIN_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call SOCKET2_APPLY_UCLIBC_IPV6_TRANSPARENT_PATCH__INT) \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	$(call LIBC_APPLY_UCLIBC_MFD_HUGE_CONSTANTS__INT) \
	$(call BOX_CAR_APPLY_ATOMICU64_MUTEX_FALLBACK__INT,$$HOME/.cargo/registry/src/*/boxcar-*/src/lib.rs) \
	$(call BOX_CAR_APPLY_ATOMICU64_MUTEX_FALLBACK__INT,$$HOME/crates/atuin-nucleo/src/boxcar.rs) \
	$(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin || CARGO_BUILD_JOBS=1 $(ATUIN_CARGO_BUILD_CMD) --target "$(ATUIN_RUST_TARGET_ARG)" --bin atuin

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg): $($(PKG)_TARGET_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(ATUIN_DIR) clean
	$(RM) $($(PKG)_BINARY) $(ATUIN_DIR)/.configured $(ATUIN_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
