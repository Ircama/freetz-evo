$(call PKG_INIT_BIN, 1.3-20230209)
$(PKG)_SOURCE:=dialog_$($(PKG)_VERSION).orig.tar.gz
$(PKG)_HASH:=0c26282305264be2217f335f3798f48b1dce3cf12c5a076bf231cadf77a6d6a8
$(PKG)_SITE:=https://deb.debian.org/debian/pool/main/d/dialog
### WEBSITE:=https://invisible-island.net/dialog/
### CHANGES:=https://invisible-island.net/dialog/CHANGES.html
### CVSREPO:=https://invisible-island.net/cgi-bin/cvsweb.cgi/dialog-snapshots/
### STEWARD:=Ircama

$(PKG)_BINARY:=$($(PKG)_DIR)/dialog
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/dialog

$(PKG)_DEPENDS_ON += ncurses

$(PKG)_CONFIGURE_OPTIONS += --with-ncurses
$(PKG)_CONFIGURE_OPTIONS += --enable-whiptail

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(DIALOG_DIR) dialog

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(DIALOG_DIR) clean

$(pkg)-uninstall:
	$(RM) $(DIALOG_TARGET_BINARY)

$(PKG_FINISH)
