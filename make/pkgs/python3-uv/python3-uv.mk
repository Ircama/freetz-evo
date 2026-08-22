$(call PKG_INIT_BIN, 0.11.16)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE:=uv-py3-$(PYTHON3_UV_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=uv-$(PYTHON3_UV_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/u/uv
$(PKG)_HASH:=4b435fcb0af8f34833dcc1903a8a223856437efd0d515c2160a2871def221238
### WEBSITE:=https://github.com/astral-sh/uv
### CVSREPO:=https://github.com/astral-sh/uv
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += $(if $(FREETZ_SEPARATE_AVM_UCLIBC),patchelf-target-host)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_UV

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_DEPENDS_VARS))
PYTHON3_UV_RUST_BUILD_STD:=std\,panic_abort
# Custom (non-builtin) targets (x86, aarch64, ...) must be passed to maturin by
# triple NAME (it cannot parse a .json path) and resolved via RUST_TARGET_PATH;
# loading them requires -Zunstable-options in both the cargo config.toml
# rustflags and the RUSTFLAGS env var (see python3-cryptography for details).
# i686/aarch64 additionally need the shared uClibc libc module patches.
PYTHON3_UV_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(PYTHON3_UV_RUST_TARGET_DIR))
PYTHON3_UV_NEEDS_AARCH64_LIBC_PATCH:=$(filter aarch64-unknown-linux-uclibc,$(PYTHON3_UV_RUST_TARGET_DIR))
PYTHON3_UV_WORKDIR:=$(abspath $(PYTHON3_UV_DIR))
PYTHON3_UV_BUILD_PATH:=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH
PYTHON3_UV_CARGO_HOME:=$(PYTHON3_UV_WORKDIR)/.cargo
PYTHON3_UV_RUSTUP_HOME:=$(HOME)/.rustup
PYTHON3_UV_XDG_CACHE_HOME:=$(PYTHON3_UV_WORKDIR)/.cache

$(PKG)_TARGET_BINARY:=$(PYTHON3_UV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$(PYTHON3_UV_TARGET_BINARY): $(PYTHON3_UV_DIR)/.configured
	cd $(PYTHON3_UV_DIR); \
	export HOME="$(PYTHON3_UV_WORKDIR)"; \
	export CARGO_HOME="$(PYTHON3_UV_CARGO_HOME)"; \
	export RUSTUP_HOME="$(PYTHON3_UV_RUSTUP_HOME)"; \
	export XDG_CACHE_HOME="$(PYTHON3_UV_XDG_CACHE_HOME)"; \
	export PATH=$(PYTHON3_UV_BUILD_PATH); \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),rustflags = ["-Zunstable-options"]\n)' \
		"$(PYTHON3_UV_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly) fetch --target "$(PYTHON3_UV_RUST_TARGET_DIR)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.3) \
	$(call SOCKET2_APPLY_UCLIBC_IPV6_TRANSPARENT_PATCH__INT) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.1) \
	$(call NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT,0.31.2) \
	# nix 0.31.x Resource enum uses repr(u32) for uclibc, but libc::RLIMIT_* are \
	# u64 on aarch64 uclibc (__rlimit_resource_t = c_ulong). Use repr(u64) there. ;\
	for nix_dir in $$HOME/.cargo/registry/src/*/nix-0.31.2; do \
		[ -d "$$nix_dir" ] || continue; \
		grep -q 'target_arch = "aarch64"), repr(u64)' "$$nix_dir/src/sys/resource.rs" || \
			perl -0pi -e 's/    #\[cfg_attr\(any\(\n            all\(target_os = "linux", any\(target_env = "gnu", target_env = "uclibc"\)\),\n            target_os = "hurd"\n        \), repr\(u32\)\)\]/    #[cfg_attr(any(\n            all(target_os = "linux", any(target_env = "gnu", target_env = "uclibc"), not(target_arch = "aarch64")),\n            target_os = "hurd"\n        ), repr(u32))]\n    #[cfg_attr(all(target_os = "linux", target_env = "uclibc", target_arch = "aarch64"), repr(u64))]/' "$$nix_dir/src/sys/resource.rs"; \
	done; \
	$(if $(PYTHON3_UV_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
	$(if $(PYTHON3_UV_NEEDS_X86_LIBC_PATCH),find "$(PYTHON3_UV_WORKDIR)/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	$(if $(PYTHON3_UV_NEEDS_AARCH64_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_AARCH64_LIBC_PATCH)) \
	$(if $(PYTHON3_UV_NEEDS_AARCH64_LIBC_PATCH),find "$(PYTHON3_UV_WORKDIR)/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	# tikv-jemalloc-sys spawns a nested `make` from its build script; the MAKEFLAGS \
	# inherited from the freetz envira wrapper may carry `-j`/--jobserver-* AFTER the \
	# `--` separator, which the nested make treats as a target ("No rule to make \
	# target '-j'"). Drop MAKEFLAGS so maturin/cargo and the nested make run cleanly. ;\
	unset MAKEFLAGS; \
	cd "$(FREETZ_BASE_DIR)"; \
	$(call Build/PyMod3/Pip, PYTHON3_UV, , \
		HOME="$(PYTHON3_UV_WORKDIR)" \
		CARGO_HOME="$(PYTHON3_UV_CARGO_HOME)" \
		RUSTUP_HOME="$(PYTHON3_UV_RUSTUP_HOME)" \
		XDG_CACHE_HOME="$(PYTHON3_UV_XDG_CACHE_HOME)" \
		PATH="$(PYTHON3_UV_BUILD_PATH)" \
		CARGO_BUILD_TARGET="$(PYTHON3_UV_RUST_TARGET_DIR)" \
		RUST_TARGET_PATH="$(FREETZ_BASE_DIR)/toolchain/rust/targets" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD=$(PYTHON3_UV_RUST_BUILD_STD)) \
		RUSTFLAGS="$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),-Zunstable-options )-C linker=$(TARGET_CROSS)gcc" \
	, isolated, no-build-ext-config)
	@if [ "$(FREETZ_SEPARATE_AVM_UCLIBC)" = "y" ]; then \
		for f in uv uvx uvw; do \
			[ -f "$(PYTHON3_UV_DEST_DIR)/usr/bin/$$f" ] || continue; \
			$(PATCHELF_TARGET) --set-interpreter $(FREETZ_LIBRARY_DIR)/ld-uClibc.so.1 $(PYTHON3_UV_DEST_DIR)/usr/bin/$$f; \
		done; \
	fi

$(pkg):

$(pkg)-precompiled: $(PYTHON3_UV_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_UV_DIR)/.configured
	$(RM) -r $(PYTHON3_UV_DIR)/build
	$(RM) -r $(PYTHON3_UV_DIR)/.cargo
	$(RM) -r $(PYTHON3_UV_DIR)/.cache

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_UV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv \
		$(PYTHON3_UV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv-*.dist-info
	$(RM) -f \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uv \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uvx \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uvw

$(PKG_FINISH)
