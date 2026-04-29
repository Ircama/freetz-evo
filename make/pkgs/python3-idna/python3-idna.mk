$(call PKG_INIT_BIN, 3.11)
$(PKG)_SOURCE:=idna-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=idna-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/i/idna
$(PKG)_HASH:=795dafcc9c04ed0c1fb032c2aa73654d8e8c5023a7df64a53f39190ada629902
### WEBSITE:=https://github.com/kjd/idna
### MANPAGE:=https://github.com/kjd/idna#readme
### CHANGES:=https://github.com/kjd/idna/blob/master/HISTORY.rst
### CVSREPO:=https://github.com/kjd/idna
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/idna/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_IDNA, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_IDNA_DIR)/.configured
	$(RM) -r $(PYTHON3_IDNA_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_IDNA_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/idna \
		$(PYTHON3_IDNA_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/idna-*.dist-info

$(PKG_FINISH)
