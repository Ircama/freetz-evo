$(call PKG_INIT_BIN, 3.0.3)
$(PKG)_SOURCE:=markupsafe-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=markupsafe-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/m/markupsafe
$(PKG)_HASH:=722695808f4b6457b320fdc131280796bdceb04ab50fe1795cd540799ebe1698
### WEBSITE:=https://palletsprojects.com/p/markupsafe/
### MANPAGE:=https://markupsafe.palletsprojects.com/
### CHANGES:=https://markupsafe.palletsprojects.com/en/latest/changes/
### CVSREPO:=https://github.com/pallets/markupsafe

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/markupsafe/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_MARKUPSAFE, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_MARKUPSAFE_DIR)/.configured
	$(RM) -r $(PYTHON3_MARKUPSAFE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_MARKUPSAFE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/markupsafe \
		$(PYTHON3_MARKUPSAFE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/MarkupSafe-*.dist-info

$(PKG_FINISH)
