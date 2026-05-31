$(call PKG_INIT_BIN, 0.14.0)
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
LNAV_CARGO_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),$(HOST_TOOLS_DIR)/usr/bin/cargo +nightly,$(HOST_TOOLS_DIR)/usr/bin/cargo)
LNAV_RUST_CONFIG_DIR:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/.cargo
LNAV_RUST_CONFIG_FILE:=$(LNAV_RUST_CONFIG_DIR)/config.toml
LNAV_RUST_MANIFEST:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/Cargo.toml
LNAV_RUST_LIB_RS:=$(LNAV_DIR)/src/third-party/lnav-rs-ext/src/lib.rs
LNAV_NEEDS_UCLIBC_RUST_FIXES:=$(filter mipsel-unknown-linux-uclibc,$(LNAV_RUST_TARGET_DIR))

$(PKG)_BINARY:=$($(PKG)_DIR)/src/lnav
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lnav

$(PKG)_DEPENDS_ON += zlib bzip2 curl libarchive libunistring ncursesw pcre2 sqlite
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_GCC_4_8_MIN),libatomic))
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_LNAV_WITH_CARGO),rust-host)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_LNAV_WITH_CARGO
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

# GitHub tag tarballs do not ship a generated configure script.
$(PKG)_CONFIGURE_PRE_CMDS += $(AUTORECONF)
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_ENV += LIBS="$(if $(FREETZ_TARGET_ARCH_MIPS),$(if $(FREETZ_TARGET_GCC_4_8_MIN),-latomic))"
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
		mkdir -p $(LNAV_RUST_CONFIG_DIR); \
		printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
			"$(LNAV_RUST_TARGET_DIR)" \
			"$(TARGET_CROSS)gcc" \
			"$(TARGET_CROSS)ar" \
			> $(LNAV_RUST_CONFIG_FILE); \
		$(LNAV_CARGO_CMD) fetch --locked --manifest-path "$(LNAV_RUST_MANIFEST)" --target "$(LNAV_RUST_TARGET_ARG)"; \
		if [ -n "$(LNAV_NEEDS_UCLIBC_RUST_FIXES)" ]; then \
			$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
			for log2src_dir in $$HOME/.cargo/git/checkouts/log2src-*/*; do \
				[ -f "$$log2src_dir/Cargo.toml" ] || continue; \
				perl -0pi -e 's/\nportable-atomic = "1\.13\.1"//g' "$$log2src_dir/Cargo.toml"; \
				perl -0pi -e 's/use portable_atomic::AtomicU64;\nuse std::sync::atomic::Ordering;/use std::sync::atomic::{AtomicUsize, Ordering};/; s/use std::sync::atomic::\{AtomicU64, Ordering\};/use std::sync::atomic::{AtomicUsize, Ordering};/; s/pub completed: AtomicU64,/pub completed: AtomicUsize,/; s/self\.completed\.load\(Ordering::Relaxed\) as u64 < self\.total/\(self.completed.load(Ordering::Relaxed) as u64\) < self.total/; s/self\.completed\.load\(Ordering::Relaxed\) < self\.total/\(self.completed.load(Ordering::Relaxed) as u64\) < self.total/; s/fetch_add\(amount, Ordering::Relaxed\)/fetch_add(amount as usize, Ordering::Relaxed)/; s/store\(self\.info\.total, Ordering::Relaxed\)/store(self.info.total as usize, Ordering::Relaxed)/; s/AtomicU64::new\(0\)/AtomicUsize::new(0)/' "$$log2src_dir/src/progress.rs"; \
			done; \
			grep -q 'LNAV_GETRANDOM_UNEXPECTED' "$(LNAV_RUST_LIB_RS)" || \
				perl -0pi -e 's~\n#\[cfg\(all\(target_os = "linux", target_env = "uclibc", target_arch = "mips"\)\)\]\n#\[no_mangle\]~\n#[cfg(all(target_os = "linux", target_env = "uclibc", target_arch = "mips"))]\n#[repr(transparent)]\nstruct LnavGetrandomError(core::num::NonZeroI32);\n\n#[cfg(all(target_os = "linux", target_env = "uclibc", target_arch = "mips"))]\nconst LNAV_GETRANDOM_UNEXPECTED: LnavGetrandomError =\n    LnavGetrandomError(unsafe { core::num::NonZeroI32::new_unchecked(65538) });\n\n#[cfg(all(target_os = "linux", target_env = "uclibc", target_arch = "mips"))]\n#[no_mangle]~' "$(LNAV_RUST_LIB_RS)"; \
			grep -q '__getrandom_v03_custom' "$(LNAV_RUST_LIB_RS)" || \
				perl -0pi -e 's~use std::time::Duration;\n~use std::time::Duration;\n\n#[cfg(all(target_os = "linux", target_env = "uclibc", target_arch = "mips"))]\n#[no_mangle]\nunsafe extern "Rust" fn __getrandom_v03_custom(\n    dest: *mut u8,\n    len: usize,\n) -> Result<(), getrandom::Error> {\n    use std::fs::File;\n    use std::io::Read;\n\n    let buf = unsafe {\n        std::ptr::write_bytes(dest, 0, len);\n        std::slice::from_raw_parts_mut(dest, len)\n    };\n    File::open("/dev/urandom")\n        .and_then(|mut file| file.read_exact(buf))\n        .map_err(|_| getrandom::Error::UNEXPECTED)\n}\n~' "$(LNAV_RUST_LIB_RS)"; \
			perl -0pi -e 's/Result<\(\), getrandom::Error>/Result<(), LnavGetrandomError>/g; s/getrandom::Error::UNEXPECTED/LNAV_GETRANDOM_UNEXPECTED/g; s/ext_prog\.completed = info\.completed\.load\(Relaxed\);/ext_prog.completed = info.completed.load(Relaxed) as u64;/' "$(LNAV_RUST_LIB_RS)"; \
		fi; \
		export CARGO_BUILD_TARGET="$(LNAV_RUST_TARGET_ARG)"; \
		export RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)"; \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),export CARGO_UNSTABLE_BUILD_STD="$(LNAV_RUST_BUILD_STD)"; ) \
		export RUSTFLAGS="$$RUSTFLAGS -C linker=$(TARGET_CROSS)gcc$(if $(LNAV_NEEDS_UCLIBC_RUST_FIXES), --cfg getrandom_backend=\"custom\" --cfg rustix_use_experimental_asm)"; \
	fi; \
	$(SUBMAKE) -C $(LNAV_DIR)

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