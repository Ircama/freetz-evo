$(call PKG_INIT_BIN, 0.9.7)
$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=768d7c580fcc592efcacac924dcfd2ebe131608f5c8ac67d36e35731e1ac683a
$(PKG)_SITE:=https://github.com/uoaerg/wavemon/archive/refs/tags
### WEBSITE:=https://github.com/uoaerg/wavemon
### MANPAGE:=https://github.com/uoaerg/wavemon#readme
### CHANGES:=https://github.com/uoaerg/wavemon/releases
### CVSREPO:=https://github.com/uoaerg/wavemon

$(PKG)_BINARY:=$($(PKG)_DIR)/wavemon
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/wavemon

$(PKG)_DEPENDS_ON += ncursesw libnl

$(PKG)_CONFIGURE_OPTIONS += --without-libcap


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(WAVEMON_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(WAVEMON_DIR) clean
	$(RM) $(WAVEMON_DIR)/.configured

$(pkg)-uninstall:
	$(RM) $(WAVEMON_TARGET_BINARY)

$(PKG_FINISH)
