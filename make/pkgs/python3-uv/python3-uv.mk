$(call PKG_INIT_BIN, 0.11.16)
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

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	cd $(PYTHON3_UV_DIR); \
	export PATH=$(HOST_TOOLS_DIR)/usr/bin:$$PATH; \
	mkdir -p .cargo; \
	printf '[target.%s]\nlinker = "%s"\nar = "%s"\n' \
		"$(PYTHON3_UV_RUST_TARGET_DIR)" \
		"$(TARGET_CROSS)gcc" \
		"$(TARGET_CROSS)ar" \
		> .cargo/config.toml
	$(call Build/PyMod3/Pip, PYTHON3_UV, , \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
		CARGO_BUILD_TARGET="$(PYTHON3_UV_RUST_TARGET_ARG)" \
		RUSTUP_TOOLCHAIN="$(if $(RUST_TARGET_NEEDS_STD_BUILD),nightly,stable)" \
		$(if $(RUST_TARGET_NEEDS_STD_BUILD),CARGO_UNSTABLE_BUILD_STD="$(PYTHON3_UV_RUST_BUILD_STD)") \
		RUSTFLAGS="-C linker=$(TARGET_CROSS)gcc" \
	, isolated, no-build-ext-config)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) -r $(PYTHON3_UV_DIR)/.configured
	$(RM) -r $(PYTHON3_UV_DIR)/build
	$(RM) -r $(PYTHON3_UV_DIR)/.cargo

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_UV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv \
		$(PYTHON3_UV_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/uv-*.dist-info
	$(RM) -f \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uv \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uvx \
		$(PYTHON3_UV_DEST_DIR)/usr/bin/uvw

$(PKG_FINISH)
