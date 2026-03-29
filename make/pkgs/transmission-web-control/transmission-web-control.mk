TRANSMISSION_WEB_CONTROL_COMMIT := cab9182a9a42329cc058555d846eabd5737ae9d4

$(call PKG_INIT_BIN, 20190919)
$(PKG)_SOURCE:=transmission-web-control-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE_DOWNLOAD_NAME:=$(TRANSMISSION_WEB_CONTROL_COMMIT).tar.gz
$(PKG)_HASH:=623aadb1c6418e6a431e45aa18468be5a02c68c0857b7850917cef30dfac585c
$(PKG)_SITE:=https://github.com/nurzico/transmission-web-control/archive
$(PKG)_TARBALL_STRIP_COMPONENTS := 1
### WEBSITE:=https://github.com/nurzico/transmission-web-control
### CHANGES:=https://github.com/nurzico/transmission-web-control/commits/master
### CVSREPO:=https://github.com/nurzico/transmission-web-control
### STEWARD:=

$(PKG)_DEPENDS_ON += transmission

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	mkdir -p $(TRANSMISSION_WEB_CONTROL_DEST_DIR)/usr/mww/transmission-web-control
	$(call COPY_USING_TAR,$(TRANSMISSION_WEB_CONTROL_DIR),$(TRANSMISSION_WEB_CONTROL_DEST_DIR)/usr/mww/transmission-web-control,--exclude='*.md' --exclude='screenshot.png' --exclude='snap-*.png' .)
	@touch $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_DIR)/.compiled

$(pkg)-clean:
	$(RM) -r $(TRANSMISSION_WEB_CONTROL_DIR)

$(pkg)-uninstall:
	$(RM) -r $(TRANSMISSION_WEB_CONTROL_DEST_DIR)/usr/mww/transmission-web-control

$(PKG_FINISH)
