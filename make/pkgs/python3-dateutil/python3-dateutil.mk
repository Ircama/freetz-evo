$(call PKG_INIT_BIN, 2.9.0.post0)
$(PKG)_SOURCE:=python-dateutil-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=python-dateutil-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/python-dateutil
$(PKG)_HASH:=37dd54208da7e1cd875388217d5e00ebd4179249f90fb72437e91a35459a0ad3
### WEBSITE:=https://github.com/dateutil/dateutil
### CHANGES:=https://dateutil.readthedocs.io/en/stable/changelog.html
### CVSREPO:=https://github.com/dateutil/dateutil

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-six

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/dateutil/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_DATEUTIL, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_DATEUTIL_DIR)/.configured
	$(RM) -r $(PYTHON3_DATEUTIL_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_DATEUTIL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/dateutil \
		$(PYTHON3_DATEUTIL_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/python_dateutil-*.dist-info

$(PKG_FINISH)
