$(call PKG_INIT_BIN, 0.148.0)
$(PKG)_SOURCE:=zeroconf-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=zeroconf-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/z/zeroconf
$(PKG)_HASH:=03fcca123df3652e23d945112d683d2f605f313637611b7d4adf31056f681702
### WEBSITE:=https://github.com/python-zeroconf/python-zeroconf
### CVSREPO:=https://github.com/python-zeroconf/python-zeroconf
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 python3-ifaddr

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zeroconf/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_ZEROCONF, , SKIP_CYTHON=1, isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_ZEROCONF_DIR)/.configured
	$(RM) -r $(PYTHON3_ZEROCONF_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_ZEROCONF_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zeroconf \
		$(PYTHON3_ZEROCONF_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/zeroconf-*.dist-info

$(PKG_FINISH)
