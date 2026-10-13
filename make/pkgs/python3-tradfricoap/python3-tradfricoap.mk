$(call PKG_INIT_BIN, 0.1.0)
$(PKG)_SOURCE:=tradfricoap-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=tradfricoap-0.1.0.tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/t/tradfricoap
$(PKG)_HASH:=5834c487999ebfe2a5226cf7c1f5d5a930927a027b09f9cf3ac9f506d324f705
### WEBSITE:=https://pypi.org/project/tradfricoap/
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-appdirs

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tradfricoap/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_TRADFRICOAP, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(PYTHON3_TRADFRICOAP_DIR)/.configured
	$(RM) -r $(PYTHON3_TRADFRICOAP_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_TRADFRICOAP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tradfricoap \
		$(PYTHON3_TRADFRICOAP_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/tradfricoap-*.dist-info

$(PKG_FINISH)
