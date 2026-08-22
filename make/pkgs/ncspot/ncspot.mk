$(call PKG_INIT_BIN, 1.3.4)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v1.3.4.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(NCSPOT_VERSION).tar.gz
$(PKG)_HASH:=93c4448b2c027c08c02295b2ffb1a48b684b65100cf4730b1dc9ae35afe06ea6
$(PKG)_SITE:=https://github.com/hrkfdn/ncspot/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/ncspot-v1.3.4
### WEBSITE:=https://github.com/hrkfdn/ncspot
### CHANGES:=https://github.com/hrkfdn/ncspot/releases
### CVSREPO:=https://github.com/hrkfdn/ncspot

$(PKG)_CATEGORY_PKGS:=Audio

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
# ncspot builds without --locked (no committed lockfile in the tarball)
NCSPOT_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(NCSPOT_CARGO_BUILD_STD_FLAGS),cargo build --release)
NCSPOT_PKG_CONFIG_DIR:=$(TARGET_TOOLCHAIN_STAGING_DIR)/lib/pkgconfig:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig:$(TARGET_MAKE_PATH)/../lib/pkgconfig
NCSPOT_CARGO_HOME:=$(abspath $(NCSPOT_DIR)/.cargo)
NCSPOT_CARGO_FEATURES:=--no-default-features --features alsa_backend,crossterm_backend
$(PKG)_BINARY:=$(NCSPOT_DIR)/target/$(NCSPOT_RUST_TARGET_DIR)/release/ncspot
$(PKG)_TARGET_BINARY:=$(NCSPOT_DEST_DIR)/usr/bin/ncspot

$(eval $(call RUST_DEPENDS_VARS))
$(PKG)_DEPENDS_ON += openssl alsa-lib

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(NCSPOT_BINARY): $(NCSPOT_DIR)/.configured
	cd $(NCSPOT_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(NCSPOT_DIR))"; \
	export CARGO_HOME="$(NCSPOT_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie -C link-arg=-latomic"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(NCSPOT_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.2) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	export OPENSSL_NO_VENDOR=1; \
	export OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"; \
	export OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"; \
	export OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"; \
	export PKG_CONFIG=/usr/bin/pkg-config; \
	export PKG_CONFIG_ALLOW_CROSS=1; \
	export PKG_CONFIG_PATH="$(NCSPOT_PKG_CONFIG_DIR)"; \
	export PKG_CONFIG_LIBDIR="$(NCSPOT_PKG_CONFIG_DIR)"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-C", "link-arg=-latomic"]\n' \
		"$(NCSPOT_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(NCSPOT_CARGO_BUILD_CMD) --target "$(NCSPOT_RUST_TARGET_ARG)" --bin ncspot $(NCSPOT_CARGO_FEATURES) || CARGO_BUILD_JOBS=1 $(NCSPOT_CARGO_BUILD_CMD) --target "$(NCSPOT_RUST_TARGET_ARG)" --bin ncspot $(NCSPOT_CARGO_FEATURES)

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(NCSPOT_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(NCSPOT_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(NCSPOT_DIR) clean
	$(RM) $(NCSPOT_BINARY) $(NCSPOT_DIR)/.configured $(NCSPOT_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(NCSPOT_TARGET_BINARY)

$(PKG_FINISH)
