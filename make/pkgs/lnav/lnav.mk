$(call PKG_INIT_BIN, 0.14.0)
# Uses a Rust/Cargo build (via make/include/rust/): requires a recent
# toolchain, gated by "depends on FREETZ_TARGET_UCLIBC_1_0_58" in Config.in.
$(PKG)_SOURCE:=lnav-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=bf142441fc85e99c256ebe661e4199768acbd340da1344554da49a9e867a49ea
$(PKG)_SITE:=https://github.com/tstack/lnav/archive/refs/tags
### WEBSITE:=https://lnav.org/
### MANPAGE:=https://docs.lnav.org/
### CHANGES:=https://github.com/tstack/lnav/releases
### CVSREPO:=https://github.com/tstack/lnav

LNAV_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
LNAV_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
LNAV_RUST_BUILD_STD:=std,panic_abort
# Custom JSON target specs (x86, aarch64, arm-BE) require -Zjson-target-spec on
# recent cargo versions, otherwise cargo errors out when lnav's own Makefile
# invokes "$$(CARGO_CMD) build --target <spec.json>".
LNAV_CARGO_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),$(HOST_TOOLS_DIR)/usr/bin/cargo +nightly$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec),$(HOST_TOOLS_DIR)/usr/bin/cargo)
LNAV_CARGO_HOME:=$(abspath $(LNAV_DIR)/.cargo)
LNAV_RUST_CONFIG_DIR:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/.cargo
LNAV_RUST_CONFIG_FILE:=$(LNAV_RUST_CONFIG_DIR)/config.toml
LNAV_RUST_MANIFEST:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/Cargo.toml
LNAV_RUST_LIB_RS:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/src/lib.rs
LNAV_RUST_TARGET_ENV:=$(subst -,_,$(LNAV_RUST_TARGET_DIR))
LNAV_NEEDS_UCLIBC_RUST_FIXES:=$(filter mips-unknown-linux-uclibc mipsel-unknown-linux-uclibc,$(LNAV_RUST_TARGET_DIR))
# The Rust `libc` crate has no x86 (32-bit) uClibc module, which breaks the
# build-std `libc` (and the app's own `libc`) on i686-unknown-linux-uclibc.
# RUST_APPLY_UCLIBC_X86_LIBC_PATCH installs the missing module.
LNAV_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(LNAV_RUST_TARGET_DIR))

$(PKG)_BINARY:=$($(PKG)_DIR)/src/lnav
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lnav

$(PKG)_DEPENDS_ON += zlib bzip2 curl libarchive libunistring ncursesw pcre2 sqlite
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_GCC_4_8_MIN),libatomic))
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_LNAV_WITH_CARGO),rust-host)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_LIB_libjemalloc),jemalloc)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_LNAV_WITH_CARGO
$(PKG)_REBUILD_SUBOPTS += FREETZ_LIB_libjemalloc
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

# GitHub tag tarballs do not ship a generated configure script.
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_ENV += LIBS="$(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_GCC_4_8_MIN),-latomic))$(if $(FREETZ_LIB_libjemalloc), -ljemalloc)"
$(PKG)_CONFIGURE_ENV += PATH="$(if $(FREETZ_PACKAGE_LNAV_WITH_CARGO),$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):)$$$$PATH"
$(PKG)_CONFIGURE_ENV += CARGO_CMD="$(if $(FREETZ_PACKAGE_LNAV_WITH_CARGO),$(LNAV_CARGO_CMD))"
$(PKG)_CONFIGURE_OPTIONS += $(if $(FREETZ_PACKAGE_LNAV_WITH_CARGO),,--without-cargo)
$(PKG)_CONFIGURE_OPTIONS += --disable-system-paths
$(PKG)_CONFIGURE_OPTIONS += --with-pcre2=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	if [ "$(FREETZ_PACKAGE_LNAV_WITH_CARGO)" = "y" ]; then \
		export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
		export HOME="$(abspath $(LNAV_DIR))"; \
		export CARGO_HOME="$(LNAV_CARGO_HOME)"; \
		export RUSTUP_HOME="$(HOME)/.rustup"; \
		mkdir -p "$(LNAV_CARGO_HOME)" $(LNAV_RUST_CONFIG_DIR); \
		printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
			"$(LNAV_RUST_TARGET_DIR)" \
			"$(TARGET_CROSS)gcc" \
			"$(TARGET_CROSS)ar" \
			> $(LNAV_RUST_CONFIG_FILE); \
		$(LNAV_CARGO_CMD) fetch --locked --manifest-path "$(LNAV_RUST_MANIFEST)" --target "$(LNAV_RUST_TARGET_ARG)"; \
		$(if $(LNAV_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
		$(if $(LNAV_NEEDS_X86_LIBC_PATCH),find "$(LNAV_DIR)/src/third-party/lnav-rs-ext/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
		if [ -n "$(LNAV_NEEDS_UCLIBC_RUST_FIXES)" ]; then \
			$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
			$(call LOG2SRC_APPLY_ATOMICU64_FALLBACK__INT) \
			$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
			perl -0pi -e 's/ext_prog\.completed = info\.completed\.load\(Relaxed\);/ext_prog.completed = info.completed.load(Relaxed) as u64;/' "$(LNAV_RUST_LIB_RS)"; \
		fi; \
		perl -0pi -e 's@^PRQLC_DIR = third-party/lnav-rs-ext/target.*@PRQLC_DIR = third-party/lnav-rs-ext/target/$(LNAV_RUST_TARGET_DIR)@m' "$(LNAV_DIR)/src/Makefile"; \
		export CARGO_BUILD_TARGET="$(LNAV_RUST_TARGET_ARG)"; \
		export CC_$(LNAV_RUST_TARGET_ENV)="$(TARGET_CROSS)gcc"; \
		export CXX_$(LNAV_RUST_TARGET_ENV)="$(TARGET_CROSS)g++"; \
		export AR_$(LNAV_RUST_TARGET_ENV)="$(TARGET_CROSS)ar"; \
		export RANLIB_$(LNAV_RUST_TARGET_ENV)="$(TARGET_CROSS)ranlib"; \
		export RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)"; \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),export CARGO_UNSTABLE_BUILD_STD="$(LNAV_RUST_BUILD_STD)"; ) \
		export RUSTFLAGS="$$RUSTFLAGS -C linker=$(TARGET_CROSS)gcc$(if $(LNAV_NEEDS_UCLIBC_RUST_FIXES), --cfg rustix_use_experimental_asm)"; \
	fi; \
	$(SUBMAKE) -C $(LNAV_DIR)/tools; \
	$(SUBMAKE) -C $(LNAV_DIR)/src all; \
	$(SUBMAKE1) -C $(LNAV_DIR)/src V=1 lnav

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	@if [ -f "$(LNAV_DIR)/Makefile" ]; then \
		$(SUBMAKE) -C $(LNAV_DIR) clean; \
	fi
	$(RM) $(LNAV_RUST_CONFIG_FILE)
	-rmdir $(LNAV_RUST_CONFIG_DIR) 2>/dev/null || true

$(pkg)-uninstall:
	$(RM) $(LNAV_TARGET_BINARY)

$(PKG_FINISH)