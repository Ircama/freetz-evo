$(call PKG_INIT_BIN, 2.2.9)
$(PKG)_SOURCE:=ulid-transform-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=ulid_transform-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/u/ulid-transform
$(PKG)_HASH:=6a8b573de0158ab4bd0424f26ed4d1cef42f15afaa718c924a8427fe24a3838f
### WEBSITE:=https://pypi.org/project/ulid-transform/
### CVSREPO:=https://github.com/ahawker/ulid-transform
### STEWARD:=Ircama

# NOTE: ulid-transform is NOT a Rust package. It is a C++ extension
# (src/ulid_transform/_ulid_impl.cpp) built via poetry-core/build_ext.py, so it
# needs no cargo/rust/maturin machinery (the RUST_* setup was dead code).
$(PKG)_DEPENDS_ON += python3

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_PYTHON3_ULID_TRANSFORM

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/ulid_transform/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ULID_TRANSFORM, , \
		PATH="$(HOST_TOOLS_DIR)/usr/bin:$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin:$(TARGET_MAKE_PATH):$$PATH" \
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
