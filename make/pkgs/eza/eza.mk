$(call PKG_INIT_BIN, 0.23.4)
include $(MAKE_DIR)/include/650-rust-cargo.mk
$(PKG)_SOURCE_DOWNLOAD_NAME:=v0.23.4.tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=9fbcad518b8a2095206ac385329ca62d216bf9fdc652dde2d082fcb37c309635
$(PKG)_SITE:=https://github.com/eza-community/eza/archive/refs/tags
$(PKG)_DIR:=$(SOURCE_DIR)/eza-0.23.4
### WEBSITE:=https://github.com/eza-community/eza
### CHANGES:=https://github.com/eza-community/eza/releases
### CVSREPO:=https://github.com/eza-community/eza

EZA_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
EZA_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
EZA_RUST_ENV_TARGET:=$(subst -,_,$(EZA_RUST_TARGET_DIR))
EZA_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
EZA_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release $(EZA_CARGO_BUILD_STD_FLAGS),cargo build --release)
EZA_CARGO_HOME:=$(abspath $(EZA_DIR)/.cargo)
$(PKG)_BINARY:=$(EZA_DIR)/target/$(EZA_RUST_TARGET_DIR)/release/eza
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/eza

$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $(EZA_DIR)/.configured
	cd $(EZA_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH; \
	export CC_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)gcc"; \
	export CXX_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)g++"; \
	export AR_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)ar"; \
	export RANLIB_$(EZA_RUST_ENV_TARGET)="$(TARGET_CROSS)ranlib"; \
	export HOME="$(abspath $(EZA_DIR))"; \
	export CARGO_HOME="$(EZA_CARGO_HOME)"; \
	export RUSTUP_HOME="$(HOME)/.rustup"; \
	mkdir -p "$$CARGO_HOME"; \
	cargo fetch --target "$(EZA_RUST_TARGET_ARG)"; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(EZA_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> "$$CARGO_HOME/config.toml"; \
	rustix_dir="$$(find "$$CARGO_HOME/registry/src" -type d -name 'rustix-1.1.2' 2>/dev/null | head -1)"; \
	if [ -n "$$rustix_dir" ] && [ ! -d "$$CARGO_HOME/rustix-1.1.2-patched" ]; then \
		cp -a "$$rustix_dir" "$$CARGO_HOME/rustix-1.1.2-patched"; \
		chmod -R u+w "$$CARGO_HOME/rustix-1.1.2-patched"; \
		perl -i -pe 's/use \{preadv64 as preadv, pwritev64 as pwritev\}/use {preadv, pwritev}/' "$$CARGO_HOME/rustix-1.1.2-patched/src/backend/libc/c.rs"; \
		perl -i -pe 's/pub const HWPOISON: Self = Self\(c::EHWPOISON\);/pub const HWPOISON: Self = Self(linux_raw_sys::general::EHWPOISON as _);/' "$$CARGO_HOME/rustix-1.1.2-patched/src/backend/libc/io/errno.rs"; \
		perl -i -pe 's/const CMSPAR = c::CMSPAR;/const CMSPAR = linux_raw_sys::general::CMSPAR as c::tcflag_t;/; s/const CRDLY = c::CRDLY;/const CRDLY = c::CRDLY as c::tcflag_t;/; s/const FFDLY = c::FFDLY;/const FFDLY = c::FFDLY as c::tcflag_t;/; s/const VTDLY = c::VTDLY;/const VTDLY = c::VTDLY as c::tcflag_t;/' "$$CARGO_HOME/rustix-1.1.2-patched/src/termios/types.rs"; \
	fi; \
	if [ -d "$$CARGO_HOME/rustix-1.1.2-patched" ]; then \
		grep -q 'rustix.*patch.crates-io' Cargo.toml || { \
			echo '' >> Cargo.toml; \
			echo '# freetz patch' >> Cargo.toml; \
			echo '[patch.crates-io]' >> Cargo.toml; \
			echo "rustix = { path = '$$CARGO_HOME/rustix-1.1.2-patched' }" >> Cargo.toml; }; \
	fi; \
	$(EZA_CARGO_BUILD_CMD) --target "$(EZA_RUST_TARGET_ARG)" --bin eza --no-default-features

$(eval $(call INSTALL_BINARY_STRIP_RULE,$($(PKG)_BINARY),/usr/bin))

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(EZA_DIR) clean
	cd $(EZA_DIR) && sed -i '/^# freetz patch/,/^\[patch.crates-io\]/,/^rustix = /d' Cargo.toml 2>/dev/null || true
	$(RM) -r $($(PKG)_BINARY) $(EZA_DIR)/.configured $(EZA_CARGO_HOME) $(EZA_DIR)/target

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_BINARY)

$(PKG_FINISH)