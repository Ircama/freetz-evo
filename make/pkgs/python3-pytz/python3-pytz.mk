$(call PKG_INIT_BIN, 2026.5)
$(PKG)_SOURCE:=pytz-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=pytz-2026.5.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/p/pytz
$(PKG)_HASH:=fa23724b9c486543b9ff54a327ee7569ac83ade54bb9afd0fc18676620401c86
### WEBSITE:=https://pypi.org/project/pytz/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pytz/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_PYTZ, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_PYTZ_DIR)/.configured
	$(RM) -r $(PYTHON3_PYTZ_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_PYTZ_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pytz \
		$(PYTHON3_PYTZ_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/pytz-*.dist-info

$(PKG_FINISH)
