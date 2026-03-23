$(call PKG_INIT_BIN, 0.16.0)
$(PKG)_SOURCE:=voluptuous-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=voluptuous-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/v/voluptuous
$(PKG)_HASH:=006535e22fed944aec17bef6e8725472476194743c87bd233e912eb463f8ff05
### WEBSITE:=https://github.com/alecthomas/voluptuous
### CHANGES:=https://github.com/alecthomas/voluptuous/releases
### CVSREPO:=https://github.com/alecthomas/voluptuous

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/voluptuous/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_VOLUPTUOUS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_VOLUPTUOUS_DIR)/.configured
	$(RM) -r $(PYTHON3_VOLUPTUOUS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_VOLUPTUOUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/voluptuous \
		$(PYTHON3_VOLUPTUOUS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/voluptuous-*.dist-info

$(PKG_FINISH)
