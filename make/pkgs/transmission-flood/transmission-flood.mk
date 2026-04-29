$(call PKG_INIT_BIN, 1.0.1)
$(PKG)_SOURCE:=transmission-flood-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=flood-for-transmission.tar.gz
$(PKG)_HASH:=0797c3d7c081665bfa876cbc78938204e1c811d5e1d09a3cb7040f365c19aa27
$(PKG)_SITE:=https://github.com/johman10/flood-for-transmission/releases/download/v$($(PKG)_VERSION)
$(PKG)_TARBALL_STRIP_COMPONENTS := 1
### WEBSITE:=https://github.com/johman10/flood-for-transmission
### CHANGES:=https://github.com/johman10/flood-for-transmission/releases
### CVSREPO:=https://github.com/johman10/flood-for-transmission
### STEWARD:=Ircama

$(PKG)_DEPENDS_ON += transmission

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	mkdir -p $(TRANSMISSION_FLOOD_DEST_DIR)/usr/mww/transmission-flood
	$(call COPY_USING_TAR,$(TRANSMISSION_FLOOD_DIR),$(TRANSMISSION_FLOOD_DEST_DIR)/usr/mww/transmission-flood,.)
	find $(TRANSMISSION_FLOOD_DEST_DIR)/usr/mww/transmission-flood -type f -name '*.js' -exec sed -i 's|\.\./rpc|../../rpc|g' {} +
	mkdir -p $(TRANSMISSION_FLOOD_DEST_DIR)/usr/share/transmission-web-home
	ln -sfn ../../mww/transmission-flood $(TRANSMISSION_FLOOD_DEST_DIR)/usr/share/transmission-web-home/transmission-flood
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(TRANSMISSION_FLOOD_DIR)

$(pkg)-uninstall:
	$(RM) -r $(TRANSMISSION_FLOOD_DEST_DIR)/usr/mww/transmission-flood
	$(RM) $(TRANSMISSION_FLOOD_DEST_DIR)/usr/share/transmission-web-home/transmission-flood

$(PKG_FINISH)
