$(call PKG_INIT_BIN, 6.0.14)
$(PKG)_SOURCE:=feedparser-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=feedparser-6.0.14.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/f/feedparser
$(PKG)_HASH:=088679b0c4b543ee211a820dd544698c76a402122eae7473c04a43425f283d06
### WEBSITE:=https://pypi.org/project/feedparser/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-feedparser-sgmllib

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_FEEDPARSER, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_FEEDPARSER_DIR)/.configured
	$(RM) -r $(PYTHON3_FEEDPARSER_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_FEEDPARSER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser \
		$(PYTHON3_FEEDPARSER_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/feedparser-*.dist-info

$(PKG_FINISH)
