$(call PKG_INIT_BIN, 2.1.19)
$(PKG)_SOURCE:=faust-cchardet-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=faust-cchardet-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/faust-cchardet
$(PKG)_HASH:=f89386297cde0c8e0f5e21464bc2d6d0e4a4fc1b1d77cdb238ca24d740d872e0
### WEBSITE:=https://github.com/faust-streaming/cChardet
### CHANGES:=https://github.com/faust-streaming/cChardet/releases
### CVSREPO:=https://github.com/faust-streaming/cChardet

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cchardet/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) "Cython>=3.0" $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) pkgconfig $(SILENT)
	$(call Build/PyMod3/Pip, PYTHON3_FAUST_CCHARDET, , \
		CPATH="$(PYTHON3_STAGING_INC_DIR)" \
		CPPFLAGS="$(TARGET_CPPFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		CXXFLAGS="$(TARGET_CXXFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_FAUST_CCHARDET_DIR)/.configured
	$(RM) -r $(PYTHON3_FAUST_CCHARDET_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FAUST_CCHARDET_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cchardet \
		$(PYTHON3_FAUST_CCHARDET_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/faust_cchardet-*.dist-info

$(PKG_FINISH)
