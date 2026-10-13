$(call PKG_INIT_BIN, 7.1.30)
$(PKG)_SOURCE:=pysnmp-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pysnmp-7.1.30.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pysnmp
$(PKG)_HASH:=db72f439b066725d2586dff068478dc8e9b303a4dba3294462b0e76b3cb63bc2
### WEBSITE:=https://pypi.org/project/pysnmp/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-pyasn1

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pysnmp/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYSNMP, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYSNMP_DIR)/.configured
	$(RM) -r $(PYTHON3_PYSNMP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYSNMP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pysnmp \
		$(PYTHON3_PYSNMP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pysnmp-*.dist-info

$(PKG_FINISH)
