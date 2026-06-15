$(call PKG_INIT_BIN, 2.2.9)
$(PKG)_SOURCE:=ulid-transform-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=ulid_transform-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/u/ulid-transform
$(PKG)_HASH:=6a8b573de0158ab4bd0424f26ed4d1cef42f15afaa718c924a8427fe24a3838f
### WEBSITE:=https://pypi.org/project/ulid-transform/
### CVSREPO:=https://github.com/ahawker/ulid-transform
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 rust-host

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_ULID_TRANSFORM
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET

PYTHON3_ULID_TRANSFORM_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
PYTHON3_ULID_TRANSFORM_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
PYTHON3_ULID_TRANSFORM_RUST_BUILD_STD:=std\,panic_abort

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ulid_transform/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd $(PYTHON3_ULID_TRANSFORM_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PYTHON3_ULID_TRANSFORM_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml
	$(call Build/PyMod3/Pip, PYTHON3_ULID_TRANSFORM, , \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
		CARGO_BUILD_TARGET="$(PYTHON3_ULID_TRANSFORM_RUST_TARGET_ARG)" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD="$(PYTHON3_ULID_TRANSFORM_RUST_BUILD_STD)") \
		RUSTFLAGS="-C linker=$(TARGET_CROSS)gcc -C link-arg=-Wl$(_comma)-no-pie" \
	, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_ULID_TRANSFORM_DIR)/.configured
	$(RM) -r $(PYTHON3_ULID_TRANSFORM_DIR)/build
	$(RM) -r $(PYTHON3_ULID_TRANSFORM_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ULID_TRANSFORM_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ulid_transform \
		$(PYTHON3_ULID_TRANSFORM_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ulid_transform-*.dist-info

$(PKG_FINISH)
