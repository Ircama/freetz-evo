$(call PKG_INIT_BIN, 2.2.0)
$(PKG)_SOURCE:=hass-nabucasa-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=hass_nabucasa-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/h/hass-nabucasa
$(PKG)_HASH:=7bfaca35cf854197cdecfd2c1e41b263e3224e1abafbb58457552021bbbed6fc
### WEBSITE:=https://github.com/NabuCasa/hass-nabucasa
### CVSREPO:=https://github.com/NabuCasa/hass-nabucasa
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3
$(PKG)_DEPENDS_ON += python3-aiohttp
$(PKG)_DEPENDS_ON += python3-attrs
$(PKG)_DEPENDS_ON += python3-ciso8601
$(PKG)_DEPENDS_ON += python3-cryptography
$(PKG)_DEPENDS_ON += python3-grpcio
$(PKG)_DEPENDS_ON += python3-voluptuous
$(PKG)_DEPENDS_ON += python3-webrtc-models
$(PKG)_DEPENDS_ON += python3-yarl

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hass_nabucasa/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_HASS_NABUCASA, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_HASS_NABUCASA_DIR)/.configured
	$(RM) -r $(PYTHON3_HASS_NABUCASA_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_HASS_NABUCASA_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hass_nabucasa \
		$(PYTHON3_HASS_NABUCASA_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/hass_nabucasa-*.dist-info

$(PKG_FINISH)
