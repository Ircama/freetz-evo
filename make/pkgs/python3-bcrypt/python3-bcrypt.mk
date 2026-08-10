$(call PKG_INIT_BIN, 5.0.0)
# Rust/Cargo cross-build requires a recent toolchain: gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in (fails on 0.9.x/1.0.14).
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE:=bcrypt-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=bcrypt-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/b/bcrypt
$(PKG)_HASH:=f748f7c2d6fd375cc93d3fba7ef4a9e3a092421b8dbf34d8d4dc06be9492dfdd
### WEBSITE:=https://github.com/pyca/bcrypt/
### CHANGES:=https://github.com/pyca/bcrypt/releases
### CVSREPO:=https://github.com/pyca/bcrypt
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_BCRYPT
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_BCRYPT_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_BCRYPT_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_BCRYPT_RUST_BUILD_STD:=std$(_comma)panic_abort
# Custom JSON target specs (x86, aarch64, ...) require -Zjson-target-spec on
# recent cargo versions (>= 1.88). The pip/setuptools-rust-internal cargo
# invocation cannot be modified, so the feature is enabled via the
# CARGO_UNSTABLE_JSON_TARGET_SPEC env var (honored on nightly, which the pip
# build already uses for build-std) and the flag is passed explicitly to the
# recipe's own cargo fetch below.
# Additionally, the Rust `libc` crate ships no x86 (32-bit) uClibc module for
# ANY 0.2.x version, so on i686 the build-std libc (and the app's own libc
# 0.2.176) must be patched with RUST_APPLY_UCLIBC_X86_LIBC_PATCH.
PYTHON3_BCRYPT_NEEDS_X86_LIBC_PATCH:=$(filter i686-unknown-linux-uclibc,$(PYTHON3_BCRYPT_RUST_TARGET_DIR))

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

PYTHON3_BCRYPT_WORKDIR:=$(abspath $(PYTHON3_BCRYPT_DIR))
PYTHON3_BCRYPT_CARGO_HOME:=$(PYTHON3_BCRYPT_WORKDIR)/.cargo
PYTHON3_BCRYPT_RUSTUP_HOME:=$(HOME)/.rustup

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd "$(PYTHON3_BCRYPT_WORKDIR)" || exit 1; \
	export HOME="$(PYTHON3_BCRYPT_WORKDIR)"; \
	export CARGO_HOME="$(PYTHON3_BCRYPT_CARGO_HOME)"; \
	export RUSTUP_HOME="$(PYTHON3_BCRYPT_RUSTUP_HOME)"; \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$$PATH; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PYTHON3_BCRYPT_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)), +nightly -Zjson-target-spec) fetch --manifest-path src/_bcrypt/Cargo.toml --target "$(PYTHON3_BCRYPT_RUST_TARGET_ARG)"; \
	for f in "$$CARGO_HOME"/registry/src/*/getrandom-0.3.3/src/backends/getrandom.rs; do \
		[ -f "$$f" ] || continue; \
		grep -q 'Freetz uClibc' "$$f" && continue; \
		perl -0pi -e 's@util_libc::sys_fill_exact\(dest, \|buf\| unsafe \{\n        libc::getrandom\(buf\.as_mut_ptr\(\)\.cast\(\), buf\.len\(\), 0\)\n    \}\)@util_libc::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc MIPS syscall fallback\n        {\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf.as_mut_ptr() as *mut libc::c_void,\n                buf.len(),\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n            ret\n        }\n    })@s' "$$f"; \
	done; \
	$(if $(PYTHON3_BCRYPT_NEEDS_X86_LIBC_PATCH),$(call RUST_APPLY_UCLIBC_X86_LIBC_PATCH)) \
	$(if $(PYTHON3_BCRYPT_NEEDS_X86_LIBC_PATCH),find "$(PYTHON3_BCRYPT_WORKDIR)/src/_bcrypt/target" -type d -path '*/.fingerprint/libc-*' -exec rm -rf {} + 2>/dev/null || true;) \
	$(call Build/PyMod3/Pip, PYTHON3_BCRYPT, , \
		HOME="$(PYTHON3_BCRYPT_WORKDIR)" \
		CARGO_HOME="$(PYTHON3_BCRYPT_CARGO_HOME)" \
		RUSTUP_HOME="$(PYTHON3_BCRYPT_RUSTUP_HOME)" \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
		CARGO_BUILD_TARGET="$(PYTHON3_BCRYPT_RUST_TARGET_ARG)" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD="$(PYTHON3_BCRYPT_RUST_BUILD_STD)") \
		$(if $(filter y,$(RUST_TARGET_NEEDS_CUSTOM_TARGET)),CARGO_UNSTABLE_JSON_TARGET_SPEC=true) \
		RUSTFLAGS="-C linker=$(TARGET_CROSS)gcc" \
		PYO3_CROSS_LIB_DIR="$(PYTHON3_STAGING_LIB_DIR)" \
		PYO3_CROSS_PYTHON_VERSION="$(PYTHON3_MAJOR_VERSION)" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_BCRYPT_DIR)/.configured
	$(RM) -r $(PYTHON3_BCRYPT_DIR)/build
	$(RM) -r $(PYTHON3_BCRYPT_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_BCRYPT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt \
		$(PYTHON3_BCRYPT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bcrypt-*.dist-info

$(PKG_FINISH)
