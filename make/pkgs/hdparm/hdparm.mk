$(call PKG_INIT_BIN, 9.65)
$(PKG)_CATEGORY:=Disk Tools
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=d14929f910d060932e717e9382425d47c2e7144235a53713d55a94f7de535a4b
$(PKG)_SITE:=@SF/$(pkg)

$(PKG)_BINARY:=$($(PKG)_DIR)/hdparm
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/hdparm

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(HDPARM_DIR) \
	CC="$(TARGET_CC)" \
	STRIP="$(TARGET_STRIP)"

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(HDPARM_DIR) clean

$(pkg)-uninstall:
	$(RM) $(HDPARM_TARGET_BINARY)

$(PKG_FINISH)
