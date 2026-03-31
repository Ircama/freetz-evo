$(call PKG_INIT_BIN, 1.8.0)
$(PKG)_SOURCE:=transmissionic-webui-$($(PKG)_VERSION).zip
$(PKG)_SOURCE_DOWNLOAD_NAME:=Transmissionic-webui-v$($(PKG)_VERSION).zip
$(PKG)_HASH:=2216c90aff525a32eca4962fe9d04aae8a0693ebc0eecab53775b33277ba3c4c
$(PKG)_SITE:=https://github.com/6c65726f79/Transmissionic/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://github.com/6c65726f79/Transmissionic
### CHANGES:=https://github.com/6c65726f79/Transmissionic/releases
### CVSREPO:=https://github.com/6c65726f79/Transmissionic
### STEWARD:=

$(PKG)_DEPENDS_ON += transmission

$(PKG_SOURCE_DOWNLOAD)

$($(PKG)_DIR)/.unpacked: $(DL_DIR)/$(TRANSMISSIONIC_WEBUI_SOURCE)
	mkdir -p $(TRANSMISSIONIC_WEBUI_DIR)
	tools/unzip $(DL_DIR)/$(TRANSMISSIONIC_WEBUI_SOURCE) -d $(TRANSMISSIONIC_WEBUI_DIR)
	@touch $@

$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	mkdir -p $(TRANSMISSIONIC_WEBUI_DEST_DIR)/usr/mww/transmissionic
	$(call COPY_USING_TAR,$(TRANSMISSIONIC_WEBUI_DIR)/web,$(TRANSMISSIONIC_WEBUI_DEST_DIR)/usr/mww/transmissionic,.)
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(TRANSMISSIONIC_WEBUI_DIR)

$(pkg)-uninstall:
	$(RM) -r $(TRANSMISSIONIC_WEBUI_DEST_DIR)/usr/mww/transmissionic

$(PKG_FINISH)
