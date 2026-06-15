$(call PKG_INIT_BIN, 0.3.18)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.3.18.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=3854293991b0dac036d640a7194be7fd71440c1e8739ffad39bab8dc651c8ade
$(PKG)_SITE:=https://github.com/achristmascarl/rainfrog/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/rainfrog-v0.3.18
### WEBSITE:=https://github.com/achristmascarl/rainfrog
### CHANGES:=https://github.com/achristmascarl/rainfrog/releases
### CVSREPO:=https://github.com/achristmascarl/rainfrog

include $(MAKE_DIR)/include/650-rust-cargo.mk

$(eval $(call RUST_TARGET_VARS))
$(eval $(call RUST_CARGO_BUILD_STD_VARS))
RAINFROG_WORKDIR:=$(abspath $(RAINFROG_DIR))
RAINFROG_BUILD_PATH:=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH
RAINFROG_CARGO_HOME:=$(RAINFROG_WORKDIR)/.cargo
RAINFROG_RUSTUP_HOME:=$(HOME)/.rustup
RAINFROG_XDG_CACHE_HOME:=$(RAINFROG_WORKDIR)/.cache

# getrandom 0.2.x uses src/getrandom.rs (not src/backends/getrandom.rs like 0.3.x)
define RAINFROG_GETRANDOM_0216_SRC_GLOB__INT
$$HOME/.cargo/registry/src/*/getrandom-0.2.16/src/getrandom.rs
endef

define RAINFROG_APPLY_GETRANDOM_0216_UCLIBC_PATCH__INT
for getrandom_src in $(call RAINFROG_GETRANDOM_0216_SRC_GLOB__INT); do \
	[ -f "$$getrandom_src" ] || continue; \
	grep -q 'Freetz uClibc' "$$getrandom_src" && continue; \
	perl -0pi -e 's@libc::getrandom\(buf_ptr, len, 0\)@// Freetz uClibc mips syscall fallback for missing libc::getrandom\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf_ptr,\n                len,\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf_ptr, len, 0)@s' "$$getrandom_src"; \
done;
endef

$(PKG)_BINARY:=$(RAINFROG_DIR)/target/$(RAINFROG_RUST_TARGET_DIR)/release/rainfrog
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/rainfrog

$(eval $(call RUST_DEPENDS_VARS))

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(RAINFROG_DIR)/.configured
	cd $(RAINFROG_DIR); \
	export HOME="$(RAINFROG_WORKDIR)"; \
	export CARGO_HOME="$(RAINFROG_CARGO_HOME)"; \
	export RUSTUP_HOME="$(RAINFROG_RUSTUP_HOME)"; \
	export XDG_CACHE_HOME="$(RAINFROG_XDG_CACHE_HOME)"; \
	export PATH=$(RAINFROG_BUILD_PATH); \
	export RUSTFLAGS="-C link-arg=-Wl,-no-pie"; \
	mkdir -p "$$CARGO_HOME"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\nrustflags = ["-C", "link-arg=-Wl,-no-pie", "-C", "link-args=-latomic"]\n' \
		"$(RAINFROG_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	cargo fetch --target "$(RAINFROG_RUST_TARGET_ARG)"; \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,1.0.8) \
	$(call RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT,0.38.44) \
	$(call GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT,0.3.3) \
	for getrandom_src in "$(RAINFROG_CARGO_HOME)/registry/src/"*"/getrandom-0.3.3/src/backends/getrandom.rs"; do \
		[ -f "$$getrandom_src" ] || continue; \
		perl -0pi -e 's@util_libc::sys_fill_exact\(dest, \|buf\| unsafe \{\n(?:.|\n)*?\n    \}\)@util_libc::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n        let ret = libc::syscall(\n            libc::SYS_getrandom,\n            buf.as_mut_ptr() as *mut libc::c_void,\n            buf.len(),\n            0,\n        ) as libc::ssize_t;\n        #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n        let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n        ret\n    })@s' "$$getrandom_src"; \
	done; \
	$(call RAINFROG_APPLY_GETRANDOM_0216_UCLIBC_PATCH__INT) \
	$(call TUI_TEXTAREA_APPLY_ATOMICU64_FALLBACK__INT,0.7.0) \
	$(RAINFROG_CARGO_BUILD_CMD) --target "$(RAINFROG_RUST_TARGET_ARG)" \
		--bin rainfrog

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(RAINFROG_DIR) clean
	$(RM) -r \
		$(RAINFROG_DIR)/.configured \
		$(RAINFROG_DIR)/.cargo \
		$(RAINFROG_DIR)/.cache \
		$(RAINFROG_DIR)/target
	$(RM) $($(PKG)_BINARY)

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)
