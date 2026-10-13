$(call PKG_INIT_BIN, 0.6)
$(PKG)_SOURCE:=micloud-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=micloud-0.6.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/micloud
$(PKG)_HASH:=46c9e66741410955a9daf39892a7e6c3e24514a46bb126e872b1ddcf6de85138
### WEBSITE:=https://pypi.org/project/micloud/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-requests

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/micloud/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_MICLOUD, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_MICLOUD_DIR)/.configured
	$(RM) -r $(PYTHON3_MICLOUD_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MICLOUD_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/micloud \
		$(PYTHON3_MICLOUD_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/micloud-*.dist-info

$(PKG_FINISH)
