$(call PKG_INIT_BIN, 2.0.0)
$(PKG)_SOURCE:=cffi-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=cffi-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/cffi
$(PKG)_HASH:=44d1b5909021139fe36001ae048dbdde8214afa20200eda0f64c068cac5d5529
### WEBSITE:=https://cffi.readthedocs.io/
### MANPAGE:=https://cffi.readthedocs.io/en/latest/
### CHANGES:=https://cffi.readthedocs.io/en/latest/whatsnew.html
### CVSREPO:=https://github.com/python-cffi/cffi
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host
$(PKG)_DEPENDS_ON += python3-pycparser
$(PKG)_DEPENDS_ON += libffi

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cffi/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_CFFI, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_CFFI_DIR)/.configured
	$(RM) -r $(PYTHON3_CFFI_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CFFI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cffi \
		$(PYTHON3_CFFI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/_cffi_backend*.so \
		$(PYTHON3_CFFI_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/cffi-*.egg-info

$(PKG_FINISH)
