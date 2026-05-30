$(call PKG_INIT_BIN, 48.0.0)
$(PKG)_SOURCE:=cryptography-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=cryptography-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/cryptography
$(PKG)_HASH:=5c3932f4436d1cccb036cb0eaef46e6e2db91035166f1ad6505c3c9d5a635920
### WEBSITE:=https://cryptography.io/
### MANPAGE:=https://cryptography.io/en/latest/
### CHANGES:=https://cryptography.io/en/latest/changelog/
### CVSREPO:=https://github.com/pyca/cryptography
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += openssl python3 python3-cffi python3-typing-extensions rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_CRYPTOGRAPHY
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_CRYPTOGRAPHY_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_CRYPTOGRAPHY_RUST_BUILD_STD:=std\,panic_abort

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd $(PYTHON3_CRYPTOGRAPHY_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml
	$(call Build/PyMod3/Pip, PYTHON3_CRYPTOGRAPHY, , \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
		OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr" \
		OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib" \
		OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include" \
		CARGO_BUILD_TARGET="$(PYTHON3_CRYPTOGRAPHY_RUST_TARGET_ARG)" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD="$(PYTHON3_CRYPTOGRAPHY_RUST_BUILD_STD)") \
		RUSTFLAGS="-C linker=$(TARGET_CROSS)gcc" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/.configured
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/build
	-$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography
	$(RM) -r $(PYTHON3_CRYPTOGRAPHY_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cryptography-$(PYTHON3_CRYPTOGRAPHY_VERSION)*.dist-info

$(PKG_FINISH)
