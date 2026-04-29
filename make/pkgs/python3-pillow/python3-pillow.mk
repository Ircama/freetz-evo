$(call PKG_INIT_BIN, 12.1.1)
$(PKG)_SOURCE:=pillow-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pillow-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pillow
$(PKG)_HASH:=9ad8fa5937ab05218e2b6a4cff30295ad35afd2f83ac592e68c0d871bb0fdbc4
### WEBSITE:=https://python-pillow.org/
### MANPAGE:=https://pillow.readthedocs.io/
### CHANGES:=https://pillow.readthedocs.io/en/stable/releasenotes/
### CVSREPO:=https://github.com/python-pillow/Pillow
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += jpeg
$(PKG)_DEPENDS_ON += libpng
$(PKG)_DEPENDS_ON += zlib

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/PIL/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade $(SILENT)
	$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --upgrade --target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) pybind11==2.13.6 $(SILENT)
	$(call Build/PyMod3/Pip, PYTHON3_PILLOW, \
		--config-settings=platform-guessing=disable, \
		CPPFLAGS="-I$(PYTHON3_STAGING_INC_DIR)" \
		CFLAGS="$(TARGET_CFLAGS) -I$(PYTHON3_STAGING_INC_DIR)" \
		LDFLAGS="$(TARGET_LDFLAGS) -L$(PYTHON3_STAGING_LIB_DIR)" \
	)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PILLOW_DIR)/.configured
	$(RM) -r $(PYTHON3_PILLOW_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PILLOW_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/PIL \
		$(PYTHON3_PILLOW_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pillow-*.egg-info

$(PKG_FINISH)
