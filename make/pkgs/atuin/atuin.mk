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
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
	done; \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	for libc_uclibc_mod in $$HOME/.cargo/registry/src/*/libc-0.2.183/src/unix/linux_like/linux/uclibc/mod.rs; do \
		[ -f "$$libc_uclibc_mod" ] || continue; \
		if ! grep -q 'MFD_HUGE_1MB' "$$libc_uclibc_mod"; then \
			perl -0pi -e 's@(pub const MAP_HUGE_16GB: c_int = 34 << MAP_HUGE_SHIFT;)@$$1\n\n// MFD_HUGE constants (from linux_l4re_shared, missing on uClibc)\npub const MFD_HUGETLB: c_uint = 0x0004;\npub const MFD_HUGE_64KB: c_uint = 0x40000000;\npub const MFD_HUGE_512KB: c_uint = 0x4c000000;\npub const MFD_HUGE_1MB: c_uint = 0x50000000;\npub const MFD_HUGE_2MB: c_uint = 0x54000000;\npub const MFD_HUGE_8MB: c_uint = 0x5c000000;\npub const MFD_HUGE_16MB: c_uint = 0x60000000;\npub const MFD_HUGE_32MB: c_uint = 0x64000000;\npub const MFD_HUGE_256MB: c_uint = 0x70000000;\npub const MFD_HUGE_512MB: c_uint = 0x74000000;\npub const MFD_HUGE_1GB: c_uint = 0x78000000;\npub const MFD_HUGE_2GB: c_uint = 0x7c000000;\npub const MFD_HUGE_16GB: c_uint = 0x88000000;\npub const MFD_HUGE_MASK: c_uint = 63;\npub const MFD_HUGE_SHIFT: c_uint = 26;@s' "$$libc_uclibc_mod"; \
		fi; \
	done; \
	for boxcar_src in $$HOME/.cargo/registry/src/*/boxcar-*/src/lib.rs; do \
		[ -f "$$boxcar_src" ] || continue; \
		if ! grep -q 'Freetz 32-bit AtomicU64 fallback' "$$boxcar_src"; then \
			perl -0pi -e 's@(use std::sync::atomic::\{AtomicBool, AtomicPtr, AtomicU64, Ordering\};)@// Freetz 32-bit AtomicU64 fallback for targets without native 64-bit atomics.\n#[cfg(target_has_atomic = "64")]\nuse std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering};\n#[cfg(not(target_has_atomic = "64"))]\nuse std::sync::{atomic::{AtomicBool, AtomicPtr, Ordering}, Mutex};\n\n#[cfg(not(target_has_atomic = "64"))]\n#[derive(Debug)]\nstruct AtomicU64(Mutex<u64>);\n\n#[cfg(not(target_has_atomic = "64"))]\nimpl AtomicU64 {\n    fn new(val: u64) -> Self { Self(Mutex::new(val)) }\n    fn load(&self, _: Ordering) -> u64 { *self.0.lock().unwrap() }\n    fn store(&self, val: u64, _: Ordering) { *self.0.lock().unwrap() = val; }\n    fn fetch_add(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock += val; prev }\n    fn fetch_or(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock |= val; prev }\n    fn into_inner(self) -> u64 { self.0.into_inner().unwrap() }\n}@s' "$$boxcar_src"; \
		fi; \
	done; \
	for atuin_boxcar_src in $$HOME/crates/atuin-nucleo/src/boxcar.rs; do \
		[ -f "$$atuin_boxcar_src" ] || continue; \
		if ! grep -q 'Freetz 32-bit AtomicU64 fallback' "$$atuin_boxcar_src"; then \
			perl -0pi -e 's@(use std::sync::atomic::\{AtomicBool, AtomicPtr, AtomicU64, Ordering\};)@// Freetz 32-bit AtomicU64 fallback for targets without native 64-bit atomics.\n#[cfg(target_has_atomic = "64")]\nuse std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering};\n#[cfg(not(target_has_atomic = "64"))]\nuse std::sync::{atomic::{AtomicBool, AtomicPtr, Ordering}, Mutex};\n\n#[cfg(not(target_has_atomic = "64"))]\n#[derive(Debug)]\nstruct AtomicU64(Mutex<u64>);\n\n#[cfg(not(target_has_atomic = "64"))]\nimpl AtomicU64 {\n    fn new(val: u64) -> Self { Self(Mutex::new(val)) }\n    fn load(&self, _: Ordering) -> u64 { *self.0.lock().unwrap() }\n    fn store(&self, val: u64, _: Ordering) { *self.0.lock().unwrap() = val; }\n    fn fetch_add(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock += val; prev }\n    fn fetch_or(&self, val: u64, _: Ordering) -> u64 { let mut lock = self.0.lock().unwrap(); let prev = *lock; *lock |= val; prev }\n    fn into_inner(self) -> u64 { self.0.into_inner().unwrap() }\n}@s' "$$atuin_boxcar_src"; \
		fi; \
	done; \
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
