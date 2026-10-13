$(call PKG_INIT_BIN, 2.10.70)
$(PKG)_SOURCE:=construct-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=construct-2.10.70.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/construct
$(PKG)_HASH:=4d2472f9684731e58cc9c56c463be63baa1447d674e0d66aeb5627b22f512c29
### WEBSITE:=https://pypi.org/project/construct/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/construct/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CONSTRUCT, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_CONSTRUCT_DIR)/.configured
	$(RM) -r $(PYTHON3_CONSTRUCT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CONSTRUCT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/construct \
		$(PYTHON3_CONSTRUCT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/construct-*.dist-info

$(PKG_FINISH)
