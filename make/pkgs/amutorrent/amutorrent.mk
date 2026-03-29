$(call PKG_INIT_BIN, 3.5.0)
$(PKG)_SOURCE:=amutorrent-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=4225e0fd786d703f60c68fb4f4dd66ceb74d27dabf123b02ccb9ef8b20f7164e
$(PKG)_SITE:=https://github.com/got3nks/amutorrent/archive/refs/tags
$(PKG)_TARBALL_STRIP_COMPONENTS := 1
### WEBSITE:=https://github.com/got3nks/amutorrent
### CHANGES:=https://github.com/got3nks/amutorrent/releases
### CVSREPO:=https://github.com/got3nks/amutorrent
### STEWARD:=

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	mkdir -p $(AMUTORRENT_DEST_DIR)/usr/mww/amutorrent
	$(call COPY_USING_TAR,$(AMUTORRENT_DIR)/static,$(AMUTORRENT_DEST_DIR)/usr/mww/amutorrent,.)
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(AMUTORRENT_DIR)

$(pkg)-uninstall:
	$(RM) -r $(AMUTORRENT_DEST_DIR)/usr/mww/amutorrent

$(PKG_FINISH)
