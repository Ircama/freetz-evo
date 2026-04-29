$(call PKG_INIT_BIN, 3.0)
$(PKG)_SOURCE:=pycparser-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pycparser-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pycparser
$(PKG)_HASH:=600f49d217304a5902ac3c37e1281c9fe94e4d0489de643a9504c5cdfdfc6b29
### WEBSITE:=https://github.com/eliben/pycparser
### CHANGES:=https://github.com/eliben/pycparser/blob/main/CHANGES
### CVSREPO:=https://github.com/eliben/pycparser
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycparser/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYCPARSER, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_PYCPARSER_DIR)/.configured
	$(RM) -r $(PYTHON3_PYCPARSER_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYCPARSER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycparser \
		$(PYTHON3_PYCPARSER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pycparser-*.dist-info

$(PKG_FINISH)
