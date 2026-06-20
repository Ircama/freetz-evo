$(call PKG_INIT_BIN, 1.29.18)
$(PKG)_SOURCE:=bluetooth-data-tools-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=bluetooth_data_tools-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/b/bluetooth-data-tools
$(PKG)_HASH:=87f678cc7b4963cb3ba73064dd72155f915bec4b21f22acd997848ddc0b1c67b
### WEBSITE:=https://github.com/bdraco/bluetooth-data-tools
### CHANGES:=https://github.com/bdraco/bluetooth-data-tools/blob/main/CHANGELOG.md
### CVSREPO:=https://github.com/bdraco/bluetooth-data-tools
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-cryptography

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bluetooth_data_tools/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_BLUETOOTH_DATA_TOOLS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_BLUETOOTH_DATA_TOOLS_DIR)/.configured
	$(RM) -r $(PYTHON3_BLUETOOTH_DATA_TOOLS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_BLUETOOTH_DATA_TOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bluetooth_data_tools \
		$(PYTHON3_BLUETOOTH_DATA_TOOLS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/bluetooth_data_tools-*.dist-info

$(PKG_FINISH)
