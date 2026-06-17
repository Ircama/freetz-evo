$(call PKG_INIT_BIN, 1.0)

$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_USR_BIN)/wish

$(PKG)_DEPENDS_ON += tk

$(PKG_UNPACKED)

$($(PKG)_TARGET_BINARY): $(TK_DIR)/unix/wish
	mkdir -p $(dir $@)
	cp -a $< $@
	$(TARGET_STRIP) $@

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	$(RM) $(WISH_TARGET_BINARY)

$(pkg)-uninstall:
	$(RM) $(WISH_TARGET_DIR)/usr/bin/wish

$(PKG_FINISH)
