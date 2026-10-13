$(call PKG_INIT_BIN, 8.5.0)
$(PKG)_SOURCE:=click-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=click-8.5.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/c/click
$(PKG)_HASH:=ba0d2089de75ea0310e2dde03160e6ca10009947fb95a182f9b54021bb272e34
### WEBSITE:=https://pypi.org/project/click/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/click/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_CLICK, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_CLICK_DIR)/.configured
	$(RM) -r $(PYTHON3_CLICK_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_CLICK_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/click \
		$(PYTHON3_CLICK_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/click-*.dist-info

$(PKG_FINISH)
