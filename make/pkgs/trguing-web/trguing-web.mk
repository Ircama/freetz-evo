$(call PKG_INIT_BIN, 1.5.1)
$(PKG)_SOURCE:=trguing-web-$($(PKG)_VERSION).zip
$(PKG)_SOURCE_DOWNLOAD_NAME:=trguing-web-v$($(PKG)_VERSION).zip
$(PKG)_HASH:=d3c7b3397989f1c343c2e2fe699b3c8fd095562adc11d590e8146c6bf4e735e8
$(PKG)_SITE:=https://github.com/openscopeproject/TrguiNG/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://github.com/openscopeproject/TrguiNG
### CHANGES:=https://github.com/openscopeproject/TrguiNG/releases
### CVSREPO:=https://github.com/openscopeproject/TrguiNG
### STEWARD:=

$(PKG)_DEPENDS_ON += transmission

$(PKG_SOURCE_DOWNLOAD)

$($(PKG)_DIR)/.unpacked: $($(PKG)_SOURCE_DOWNLOAD_TIMESTAMP)
	mkdir -p $(TRGUING_WEB_DIR)
	tools/unzip $(DL_DIR)/$(TRGUING_WEB_SOURCE) -d $(TRGUING_WEB_DIR)
	@touch $@

$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	mkdir -p $(TRGUING_WEB_DEST_DIR)/usr/mww/trguing
	$(call COPY_USING_TAR,$(TRGUING_WEB_DIR),$(TRGUING_WEB_DEST_DIR)/usr/mww/trguing,.)
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(TRGUING_WEB_DIR)

$(pkg)-uninstall:
	$(RM) -r $(TRGUING_WEB_DEST_DIR)/usr/mww/trguing

$(PKG_FINISH)
