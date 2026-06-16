$(call PKG_INIT_BIN, 410)
$(PKG)_SOURCE:=$(pkg).tar.gz
$(PKG)_HASH:=7ba9fbb303dd3d95d06ca24360d019048d84e5822dc6fe722cd77369bdbf231f
$(PKG)_SITE:=https://invisible-island.net/datafiles/release
### WEBSITE:=https://invisible-island.net/xterm/

$(PKG)_BINARY:=$($(PKG)_DIR)/xterm
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_USR_BIN)/xterm

$(PKG)_DEPENDS_ON += libX11 libXt libXext libXmu
$(PKG)_DEPENDS_ON += ncurses
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --disable-freetype
$(PKG)_CONFIGURE_OPTIONS += --disable-toolbar
$(PKG)_CONFIGURE_OPTIONS += --disable-wide-chars
$(PKG)_CONFIGURE_OPTIONS += --disable-wide-attrs

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XTERM_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)
	# Also install resize binary
	mkdir -p $(dir $($(PKG)_DEST_USR_BIN)/resize)
	$(INSTALL_FILE) $(XTERM_DIR)/resize $($(PKG)_DEST_USR_BIN)/resize
	$(TARGET_STRIP) $($(PKG)_DEST_USR_BIN)/resize

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(XTERM_DIR) clean

$(pkg)-uninstall:
	$(RM) $(XTERM_TARGET_BINARY)
	$(RM) $($(PKG)_DEST_USR_BIN)/resize

$(PKG_FINISH)
