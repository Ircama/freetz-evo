$(call PKG_INIT_BIN, 0.4.2)
$(PKG)_SOURCE:=pyasn1-modules-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pyasn1_modules-0.4.2.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pyasn1-modules
$(PKG)_HASH:=677091de870a80aae844b1ca6134f54652fa2c8c5a52aa396440ac3106e941e6
### WEBSITE:=https://pypi.org/project/pyasn1-modules/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-pyasn1

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1_modules/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYASN1_MODULES, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYASN1_MODULES_DIR)/.configured
	$(RM) -r $(PYTHON3_PYASN1_MODULES_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYASN1_MODULES_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1_modules \
		$(PYTHON3_PYASN1_MODULES_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pyasn1_modules-*.dist-info

$(PKG_FINISH)
