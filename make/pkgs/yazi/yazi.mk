$(call PKG_INIT_BIN, 26.5.6)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58" in Config.in (fails on 0.9.x/1.0.14).
$(PKG)_SOURCE_DOWNLOAD_NAME:=v26.5.6.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=a18445df86a20068f7b17609d12d6f635de488958579ae7a2b143a244ba7e63f
$(PKG)_SITE:=https://github.com/sxyazi/yazi/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/yazi-v26.5.6
### WEBSITE:=https://github.com/sxyazi/yazi
### CHANGES:=https://github.com/sxyazi/yazi/releases
### CVSREPO:=https://github.com/sxyazi/yazi

YAZI_PKG_DIR:=$(realpath $(dir $(lastword $(MAKEFILE_LIST))))

include $(MAKE_DIR)/include/650-rust-cargo.mk

YAZI_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
YAZI_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
YAZI_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), -Zjson-target-spec)
YAZI_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $(YAZI_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
YAZI_CARGO_HOME:=$(abspath $(YAZI_DIR)/.cargo)
$(PKG)_BINARY_YAZI:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/yazi
$(PKG)_BINARY_YA:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/ya
$(PKG)_TARGET_BINARY_YAZI:=$($(PKG)_DEST_DIR)/usr/bin/yazi
$(PKG)_TARGET_BINARY_YA:=$($(PKG)_DEST_DIR)/usr/bin/ya

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY_YAZI) $($(PKG)_BINARY_YA): $(YAZI_DIR)/.configured
	cd $(YAZI_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(YAZI_DIR))"; \
	export CARGO_HOME="$(YAZI_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie"; \
	mkdir -p "$$CARGO_HOME"; \
	# Fetch all deps so we can patch source files before build ;\
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(YAZI_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	# Apply getrandom uClibc MIPS syscall patch for missing libc::getrandom ;\
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	# Apply rustix uClibc patches for missing libc symbols ;\
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	# Apply socket2 IPV6_TRANSPARENT fix for uClibc ;\
	for socket2_src in $$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs; do \
		[ -f "$$socket2_src" ] || continue; \
		sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
		echo "Patched socket2: $$socket2_src" >&2; \
	done; \
	# Apply AtomicU64→Mutex fix for async-priority-channel dependency ;\
	for apc_src in $$HOME/.cargo/registry/src/*/async-priority-channel-0.2.0/src/awaitable_atomics.rs; do \
		[ -f "$$apc_src" ] || continue; \
		python3 -c "import re,sys;c=open(sys.argv[1]).read();c=c.replace('sync::atomic::{AtomicU64, Ordering}','sync::Mutex');c=c.replace('value: AtomicU64,','value: Mutex<u64>,');c=c.replace('value: AtomicU64::new(value),','value: Mutex::new(value),');c=c.replace('self.value.fetch_or(U64_TOP_BIT_MASK, Ordering::SeqCst)','{ let mut v = self.value.lock().unwrap(); let prior = *v; *v = prior | U64_TOP_BIT_MASK; prior }');c=c.replace('self.value.fetch_add(n, Ordering::SeqCst)','{ let mut v = self.value.lock().unwrap(); let prior = *v; *v = prior + n; prior }');c=c.replace('self.value.fetch_sub(1, Ordering::SeqCst)','{ let mut v = self.value.lock().unwrap(); let prior = *v; *v = prior - 1; prior }');c=c.replace('self.value.load(Ordering::SeqCst)','*self.value.lock().unwrap()');open(sys.argv[1],'w').write(c);print('Patched async-priority-channel')" "$$apc_src"; \
	done; \
	# Apply AtomicU64→AtomicU32 fix for yazi workspace (MIPS uClibc has no AtomicU64) ;\
	python3 "$(YAZI_PKG_DIR)/patches/patch-yazi-shared-atomic64.py" && \
	echo "Patched yazi-shared AtomicU64 -> AtomicU32/Mutex" >&2; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie"]\n' \
		"$(YAZI_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(YAZI_CARGO_BUILD_CMD) --target "$(YAZI_RUST_TARGET_ARG)" --bin yazi --bin ya

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY_YAZI),/usr/bin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY_YA),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY_YAZI) $($(PKG)_TARGET_BINARY_YA)

$(pkg)-clean:
	-$(SUBMAKE) -C $(YAZI_DIR) clean
	$(RM) $($(PKG)_BINARY_YAZI) $($(PKG)_BINARY_YA) $(YAZI_DIR)/.configured $(YAZI_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY_YAZI) $($(PKG)_TARGET_BINARY_YA)

$(PKG_FINISH)
