$(call PKG_INIT_BIN, 6.2)
$(PKG)_SOURCE:=zope.event-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=zope_event-6.2.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/z/zope.event
$(PKG)_HASH:=b97d5d6327067ee6b9dfcbdf606ade9ade70991e19c162e808ea39e5fcf0f8d3
### WEBSITE:=https://pypi.org/project/zope.event/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope/event/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ZOPE_EVENT, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_ZOPE_EVENT_DIR)/.configured
	$(RM) -r $(PYTHON3_ZOPE_EVENT_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ZOPE_EVENT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope/event \
		$(PYTHON3_ZOPE_EVENT_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope_event-*.dist-info

$(PKG_FINISH)
