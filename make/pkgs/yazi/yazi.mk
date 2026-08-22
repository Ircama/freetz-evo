$(call PKG_INIT_BIN, 26.5.6)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
$(PKG)_SOURCE_DOWNLOAD_NAME:=v26.5.6.tar.gz
$(PKG)_SOURCE:=$(pkg)-$(YAZI_VERSION).tar.gz
$(PKG)_HASH:=a18445df86a20068f7b17609d12d6f635de488958579ae7a2b143a244ba7e63f
$(PKG)_SITE:=https://github.com/sxyazi/yazi/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/yazi-v26.5.6
### WEBSITE:=https://github.com/sxyazi/yazi
### CHANGES:=https://github.com/sxyazi/yazi/releases
### CVSREPO:=https://github.com/sxyazi/yazi

YAZI_PKG_DIR:=$(realpath $(dir $(lastword $(MAKEFILE_LIST))))

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
YAZI_CARGO_HOME:=$(abspath $(YAZI_DIR)/.cargo)
$(PKG)_BINARY_YAZI:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/yazi
$(PKG)_BINARY_YA:=$(YAZI_DIR)/target/$(YAZI_RUST_TARGET_DIR)/release/ya
$(PKG)_TARGET_BINARY_YAZI:=$(YAZI_DEST_DIR)/usr/bin/yazi
$(PKG)_TARGET_BINARY_YA:=$(YAZI_DEST_DIR)/usr/bin/ya

$(eval $(call RUST_DEPENDS_VARS))
# yazi builds two binaries; tie both to the custom target spec file
$(YAZI_BINARY_YAZI) $(YAZI_BINARY_YA): $(RUST_TARGET_SPEC_FILE)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(YAZI_BINARY_YAZI) $(YAZI_BINARY_YA): $(YAZI_DIR)/.configured
	cd $(YAZI_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export HOME="$(abspath $(YAZI_DIR))"; \
	export CARGO_HOME="$(YAZI_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie"; \
	# tikv-jemalloc-sys spawns a nested `make` from its build script; the MAKEFLAGS \
	# inherited from the freetz envira wrapper may carry `-j`/--jobserver-* AFTER the \
	# `--` separator, which the nested make treats as a target ("No rule to make \
	# target '-j'"). Drop MAKEFLAGS so nested makes run without the broken flags. ;\
	unset MAKEFLAGS; \
	mkdir -p "$$CARGO_HOME"; \
	# Fetch all deps so we can patch source files before build ;\
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(YAZI_RUST_TARGET_ARG)" $(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zjson-target-spec); \
	$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH) \
	$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH) \
	# Apply getrandom uClibc MIPS syscall patch for missing libc::getrandom ;\
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.2) \
	# Apply rustix uClibc patches for missing libc symbols ;\
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	# Apply socket2 IPV6_TRANSPARENT fix for uClibc ;\
	$(call SOCKET2_APPLY_UCLIBC_IPV6_TRANSPARENT_PATCH__INT) \
	# Apply AtomicU64→Mutex fix for async-priority-channel dependency ;\
	$(call ASYNC_PRIORITY_CHANNEL_APPLY_ATOMICU64_MUTEX_FALLBACK__INT) \
	# Apply AtomicU64→AtomicU32 fix for yazi workspace (MIPS uClibc has no AtomicU64) ;\
	python3 "$(YAZI_PKG_DIR)/patches/patch-yazi-shared-atomic64.py" && \
	echo "Patched yazi-shared AtomicU64 -> AtomicU32/Mutex" >&2; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie"]\n' \
		"$(YAZI_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	$(YAZI_CARGO_BUILD_CMD) --target "$(YAZI_RUST_TARGET_ARG)" --bin yazi --bin ya

$(eval $(call INSTALL_BINARY_STRIP_RULE,$(YAZI_BINARY_YAZI),/usr/bin))
$(eval $(call INSTALL_BINARY_STRIP_RULE,$(YAZI_BINARY_YA),/usr/bin))

$(pkg):

$(pkg)-precompiled: $(YAZI_TARGET_BINARY_YAZI) $(YAZI_TARGET_BINARY_YA)

$(pkg)-clean:
	-$(SUBMAKE) -C $(YAZI_DIR) clean
	$(RM) $(YAZI_BINARY_YAZI) $(YAZI_BINARY_YA) $(YAZI_DIR)/.configured $(YAZI_DIR)/.cargo/config.toml

$(pkg)-uninstall:
	$(RM) $(YAZI_TARGET_BINARY_YAZI) $(YAZI_TARGET_BINARY_YA)

$(PKG_FINISH)
