$(call PKG_INIT_BIN, 2.1.0)
$(PKG)_SOURCE:=feedparser-sgmllib-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=feedparser_sgmllib-2.1.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/feedparser-sgmllib
$(PKG)_HASH:=61facf2918c4389b5b00714f76c5e03431ffcd94cd1f51d657edd6cd7c396579
### WEBSITE:=https://pypi.org/project/feedparser-sgmllib/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser_sgmllib/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_FEEDPARSER_SGMLLIB, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_FEEDPARSER_SGMLLIB_DIR)/.configured
	$(RM) -r $(PYTHON3_FEEDPARSER_SGMLLIB_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FEEDPARSER_SGMLLIB_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser_sgmllib \
		$(PYTHON3_FEEDPARSER_SGMLLIB_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser_sgmllib-*.dist-info

$(PKG_FINISH)
