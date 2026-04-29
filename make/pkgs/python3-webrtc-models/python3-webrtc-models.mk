$(call PKG_INIT_BIN, 0.3.0)
$(PKG)_SOURCE:=webrtc-models-py3-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=webrtc_models-$($(PKG)_VERSION).tar.gz
$(PKG)_SITE:=https://files.pythonhosted.org/packages/source/w/webrtc-models
$(PKG)_HASH:=559c743e5cc3bcc8133be1b6fb5e8492a9ddb17151129c21cbb2e3f2a1166526
### WEBSITE:=https://github.com/home-assistant-libs/webrtc-models
### CVSREPO:=https://github.com/home-assistant-libs/webrtc-models
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += python3 python3-mashumaro python3-orjson

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/webrtc_models/__init__.py

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_TARGET_BINARY): $($(PKG)_DIR)/.configured
	$(call Build/PyMod3/Pip, PYTHON3_WEBRTC_MODELS, , , isolated)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	$(RM) $(PYTHON3_WEBRTC_MODELS_DIR)/.configured
	$(RM) -r $(PYTHON3_WEBRTC_MODELS_DIR)/build

$(pkg)-uninstall:
	$(RM) -r \
		$(PYTHON3_WEBRTC_MODELS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/webrtc_models \
		$(PYTHON3_WEBRTC_MODELS_DEST_DIR)$(PYTHON3_SITE_PKG_DIR)/webrtc_models-*.dist-info

$(PKG_FINISH)
