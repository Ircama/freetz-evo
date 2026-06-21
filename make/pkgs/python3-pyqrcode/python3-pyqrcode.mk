$(call PKG_INIT_BIN, 1.2.1)
$(PKG)_SOURCE:=pyqrcode-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=PyQRCode-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/P/PyQRCode
$(PKG)_HASH:=fdbf7634733e56b72e27f9bce46e4550b75a3a2c420414035cae9d9d26b234d5
### WEBSITE:=https://pypi.org/project/PyQRCode/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyqrcode/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYQRCODE, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYQRCODE_DIR)/.configured
	$(RM) -r $(PYTHON3_PYQRCODE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYQRCODE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyqrcode \
		$(PYTHON3_PYQRCODE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/PyQRCode-*.dist-info \
		$(PYTHON3_PYQRCODE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyqrcode-*.dist-info

$(PKG_FINISH)
