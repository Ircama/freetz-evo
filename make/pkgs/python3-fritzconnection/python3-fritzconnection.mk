$(call PKG_INIT_BIN, 1.15.1)
$(PKG)_SOURCE:=fritzconnection-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=fritzconnection-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/fritzconnection
$(PKG)_HASH:=aa40b0a850f65fd7ea0483e65f733aa534d63c5e5bb9a8306c63e9dfd0bcf5dd
### WEBSITE:=https://fritzconnection.readthedocs.io/
### CHANGES:=https://github.com/kbr/fritzconnection/releases
### CVSREPO:=https://github.com/kbr/fritzconnection
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-requests

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fritzconnection/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_FRITZCONNECTION, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_FRITZCONNECTION_DIR)/.configured
	$(RM) -r $(PYTHON3_FRITZCONNECTION_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FRITZCONNECTION_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fritzconnection \
		$(PYTHON3_FRITZCONNECTION_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/fritzconnection-*.dist-info

$(PKG_FINISH)
