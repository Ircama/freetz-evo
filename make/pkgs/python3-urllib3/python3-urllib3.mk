$(call PKG_INIT_BIN, 2.8.0)
$(PKG)_SOURCE:=urllib3-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=urllib3-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/u/urllib3
$(PKG)_HASH:=63bf2ead4c879426ebf22ef2a781eeb4aa3b4ae798a0435506f8687fd5bb9b63
### WEBSITE:=https://github.com/urllib3/urllib3
### CHANGES:=https://github.com/urllib3/urllib3/releases
### CVSREPO:=https://github.com/urllib3/urllib3
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/urllib3/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_URLLIB3, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_URLLIB3_DIR)/.configured
	$(RM) -r $(PYTHON3_URLLIB3_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_URLLIB3_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/urllib3 \
		$(PYTHON3_URLLIB3_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/urllib3-*.dist-info

$(PKG_FINISH)
