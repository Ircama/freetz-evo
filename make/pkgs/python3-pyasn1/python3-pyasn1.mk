$(call PKG_INIT_BIN, 0.6.4)
$(PKG)_SOURCE:=pyasn1-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyasn1-0.6.4.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyasn1
$(PKG)_HASH:=9c447d8431c947fe4c8febc4ed9e760bc29011a5b01e5c74b67025bd9fb8ce81
### WEBSITE:=https://pypi.org/project/pyasn1/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYASN1, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYASN1_DIR)/.configured
	$(RM) -r $(PYTHON3_PYASN1_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYASN1_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1 \
		$(PYTHON3_PYASN1_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1-*.dist-info

$(PKG_FINISH)
