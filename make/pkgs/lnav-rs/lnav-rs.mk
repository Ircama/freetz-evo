$(call PKG_INIT_BIN, 0.1.0)
include $(MAKE_DIR)/include/650-rust-cargo.mk
# Upstream has no release tags yet; pin a known main-branch snapshot.
$(PKG)_SOURCE_DOWNLOAD_NAME:=3f27b3db563b18c33db328a6b6fbf74f5b2ddd03.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4b4f61bb50337f6fce6b86a0adfead4745db57ec815a6a8a1ff214dba1a11e1a
$(PKG)_SITE:=https://github.com/huskercane/lnav-rs/archive
$(PKG)_DIR:=$(SOURCE_DIR)/lnav-rs-3f27b3db563b18c33db328a6b6fbf74f5b2ddd03
### WEBSITE:=https://github.com/huskercane/lnav-rs
### CHANGES:=https://github.com/huskercane/lnav-rs/commits/main
### CVSREPO:=https://github.com/huskercane/lnav-rs

LNAV_RS_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
LNAV_RS_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
LNAV_RS_NEEDS_UCLIBC_MIPS_WORKAROUNDS:=$(filter mips-unknown-linux-uclibc mipsel-unknown-linux-uclibc,$(LNAV_RS_RUST_TARGET_DIR))
LNAV_RS_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
LNAV_RS_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(LNAV_RS_CARGO_BUILD_STD_FLAGS),cargo build --release)
LNAV_RS_CARGO_HOME:=$(abspath $(LNAV_RS_DIR)/.cargo)
$(PKG)_BINARY:=$(LNAV_RS_DIR)/target/$(LNAV_RS_RUST_TARGET_DIR)/release/lnav-rs
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/lnav-rs

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(LNAV_RS_DIR)/.configured
	cd $(LNAV_RS_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(LNAV_RS_DIR))"; \
	export CARGO_HOME="$(LNAV_RS_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo fetch --target "$(LNAV_RS_RUST_TARGET_ARG)"; \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	if [ -n "$(LNAV_RS_NEEDS_UCLIBC_MIPS_WORKAROUNDS)" ]; then \
		grep -q 'tempfile = "=3.17.1"' crates/cli/Cargo.toml || \
			printf "%s\n%s\n%s\n%s\n" "" "[target.'cfg(all(target_os = \"linux\", target_env = \"uclibc\", target_arch = \"mips\"))'.dependencies]" "getrandom = \"=0.3.4\"" "tempfile = \"=3.17.1\"" >> crates/cli/Cargo.toml; \
		grep -q 'version = "=53.1.0"' crates/query/Cargo.toml || \
			perl -0pi -e 's~datafusion = \{ version = "53\.0\.0", default-features = false, features = \["sql"\] \}~datafusion = { version = "=53.1.0", default-features = false, features = ["sql"] }~' crates/query/Cargo.toml; \
		grep -q '__getrandom_v03_custom' crates/cli/src/main.rs || \
			perl -0pi -e 's~use std::time::\{Duration, Instant\};\n~use std::time::{Duration, Instant};\n\n#[cfg(all(target_os = "linux", target_env = "uclibc", target_arch = "mips"))]\n#[no_mangle]\nunsafe extern "Rust" fn __getrandom_v03_custom(\n    dest: *mut u8,\n    len: usize,\n) -> Result<(), getrandom::Error> {\n    use std::fs::File;\n    use std::io::Read;\n\n    let buf = unsafe {\n        std::ptr::write_bytes(dest, 0, len);\n        std::slice::from_raw_parts_mut(dest, len)\n    };\n    File::open("/dev/urandom")\n        .and_then(|mut file| file.read_exact(buf))\n        .map_err(|_| getrandom::Error::UNEXPECTED)\n}\n~' crates/cli/src/main.rs; \
		export RUSTFLAGS="$$RUSTFLAGS --cfg getrandom_backend=\"custom\" --cfg rustix_use_experimental_asm"; \
	fi; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(LNAV_RS_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	if [ -n "$(LNAV_RS_NEEDS_UCLIBC_MIPS_WORKAROUNDS)" ]; then \
		cargo +nightly fetch --target "$(LNAV_RS_RUST_TARGET_ARG)"; \
		datafusion_dir="$$(find "$$CARGO_HOME/registry/src" -path '*/datafusion-execution-53.1.0' -type d | head -n 1)"; \
		test -n "$$datafusion_dir" || exit 1; \
		grep -q 'type CompatAtomicU64 = Mutex<u64>;' "$$datafusion_dir/src/disk_manager.rs" || \
			patch -N -d "$$datafusion_dir" -p1 < "$(abspath make/pkgs/lnav-rs/registry-patches/010-datafusion-execution-no-atomic64.patch)"; \
	fi; \
	$(LNAV_RS_CARGO_BUILD_CMD) --target "$(LNAV_RS_RUST_TARGET_ARG)" -p lnav-rs

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LNAV_RS_DIR) clean
	$(RM) $($(PKG)_BINARY) $(LNAV_RS_DIR)/.configured $(LNAV_RS_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
