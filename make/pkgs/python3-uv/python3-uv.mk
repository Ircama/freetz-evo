$(call PKG_INIT_BIN, 0.11.16)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE:=uv-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=uv-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/u/uv
$(PKG)_HASH:=4b435fcb0af8f34833dcc1903a8a223856437efd0d515c2160a2871def221238
### WEBSITE:=https://github.com/astral-sh/uv
### CVSREPO:=https://github.com/astral-sh/uv
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_UV
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_UV_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_UV_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_UV_RUST_BUILD_STD:=std\,panic_abort
PYTHON3_UV_WORKDIR:=$(abspath $(PYTHON3_UV_DIR))
PYTHON3_UV_BUILD_PATH:=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH
PYTHON3_UV_CARGO_HOME:=$(PYTHON3_UV_WORKDIR)/.cargo
PYTHON3_UV_RUSTUP_HOME:=$(HOME)/.rustup
PYTHON3_UV_XDG_CACHE_HOME:=$(PYTHON3_UV_WORKDIR)/.cache

define PYTHON3_UV_GETRANDOM_033_BACKEND_GLOB__INT
$$HOME/.cargo/registry/src/*/getrandom-0.3.3/src/backends/getrandom.rs
endef

define PYTHON3_UV_APPLY_GETRANDOM_033_UCLIBC_PATCH__INT
for getrandom_src in $(call PYTHON3_UV_GETRANDOM_033_BACKEND_GLOB__INT); do \
	[ -f "$$getrandom_src" ] || continue; \
	grep -q 'Freetz uClibc' "$$getrandom_src" && continue; \
	perl -0pi -e 's@util_libc::sys_fill_exact\(dest, \|buf\| unsafe \{\n        libc::getrandom\(buf\.as_mut_ptr\(\)\.cast\(\), buf\.len\(\), 0\)\n    \}\)@util_libc::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom\n        {\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf.as_mut_ptr() as *mut libc::c_void,\n                buf.len(),\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n            ret\n        }\n    })@s' "$$getrandom_src"; \
done;
endef

define PYTHON3_UV_SOCKET2_063_SRC_GLOB__INT
$$HOME/.cargo/registry/src/*/socket2-0.6.3/src/socket.rs
endef

define PYTHON3_UV_APPLY_SOCKET2_063_UCLIBC_PATCH__INT
for socket2_src in $(call PYTHON3_UV_SOCKET2_063_SRC_GLOB__INT); do \
	[ -f "$$socket2_src" ] || continue; \
	sed -i 's/libc::IPV6_TRANSPARENT/libc::IP_TRANSPARENT/g' "$$socket2_src"; \
done;
endef

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd $(PYTHON3_UV_DIR); \
	export HOME="$(PYTHON3_UV_WORKDIR)"; \
	export CARGO_HOME="$(PYTHON3_UV_CARGO_HOME)"; \
	export RUSTUP_HOME="$(PYTHON3_UV_RUSTUP_HOME)"; \
	export XDG_CACHE_HOME="$(PYTHON3_UV_XDG_CACHE_HOME)"; \
	export PATH=$(PYTHON3_UV_BUILD_PATH); \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PYTHON3_UV_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo fetch --target "$(PYTHON3_UV_RUST_TARGET_ARG)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT,1.1.4) \
	$(call PYTHON3_UV_APPLY_GETRANDOM_033_UCLIBC_PATCH__INT) \
	$(call PYTHON3_UV_APPLY_SOCKET2_063_UCLIBC_PATCH__INT) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.4.1) \
	$(call NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT,0.31.2)
	$(call Build/PyMod3/Pip, PYTHON3_UV, , \
		HOME="$(PYTHON3_UV_WORKDIR)" \
		CARGO_HOME="$(PYTHON3_UV_CARGO_HOME)" \
		RUSTUP_HOME="$(PYTHON3_UV_RUSTUP_HOME)" \
		XDG_CACHE_HOME="$(PYTHON3_UV_XDG_CACHE_HOME)" \
		PATH="$(PYTHON3_UV_BUILD_PATH)" \
		CARGO_BUILD_TARGET="$(PYTHON3_UV_RUST_TARGET_ARG)" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD=$(PYTHON3_UV_RUST_BUILD_STD)) \
		RUSTFLAGS="-C linker=$(TARGET_CROSS)gcc -C link-arg=-Wl,-no-pie" \
	, isolated, no-build-ext-config)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


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
