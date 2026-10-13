$(call PKG_INIT_BIN, 0.7.1)
$(PKG)_SOURCE:=defusedxml-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=defusedxml-0.7.1.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/d/defusedxml
$(PKG)_HASH:=1bb3032db185915b62d7c6209c5a8792be6a32ab2fedacc84e01b52c51aa3e69
### WEBSITE:=https://pypi.org/project/defusedxml/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/defusedxml/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_DEFUSEDXML, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_DEFUSEDXML_DIR)/.configured
	$(RM) -r $(PYTHON3_DEFUSEDXML_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_DEFUSEDXML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/defusedxml \
		$(PYTHON3_DEFUSEDXML_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/defusedxml-*.dist-info

$(PKG_FINISH)
