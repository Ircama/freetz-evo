$(call PKG_INIT_BIN, 8.6)
$(PKG)_SOURCE:=zope.interface-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=zope_interface-8.6.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/z/zope.interface
$(PKG)_HASH:=b40ef9b4873afb5d0dec02b8d2dfde1cf18c72337b60c99cb735961e0bac05c0
### WEBSITE:=https://pypi.org/project/zope.interface/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-setuptools-host

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope/interface/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/PKG, PYTHON3_ZOPE_INTERFACE, , )

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_ZOPE_INTERFACE_DIR)/.configured
	$(RM) -r $(PYTHON3_ZOPE_INTERFACE_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ZOPE_INTERFACE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope/interface \
		$(PYTHON3_ZOPE_INTERFACE_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zope_interface-*.dist-info

$(PKG_FINISH)
