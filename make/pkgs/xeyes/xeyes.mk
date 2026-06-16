$(call PKG_INIT_BIN, 1.3.1)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=5608d76b7b1aac5ed7f22f1b6b5ad74ef98c8693220f32b4b87dccee4a956eaa
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/app
### WEBSITE:=https://www.x.org/

$(PKG)_BINARY:=$($(PKG)_DIR)/xeyes
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_USR_BIN)/xeyes

$(PKG)_DEPENDS_ON += libXi libXmu libX11 libXt libXext
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --without-xrender
$(PKG)_CONFIGURE_OPTIONS += --without-present

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XEYES_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(XEYES_DIR) clean

$(pkg)-uninstall:
	$(RM) $(XEYES_TARGET_BINARY)

$(PKG_FINISH)
