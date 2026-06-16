$(call PKG_INIT_BIN, 1.1.1)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=df7ceabf8f07044a2fde4924d794554996811640a45de40cb12c2cf1f90f742c
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/app
### WEBSITE:=https://www.x.org/

$(PKG)_BINARY:=$($(PKG)_DIR)/xclock
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_USR_BIN)/xclock

$(PKG)_DEPENDS_ON += libXaw libXmu libX11 libXext libXt
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --without-xft
$(PKG)_CONFIGURE_OPTIONS += --without-xkb

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XCLOCK_DIR)

$($(PKG)_TARGET_BINARY): $($(PKG)_BINARY)
	$(INSTALL_BINARY_STRIP)

$(pkg):

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(XCLOCK_DIR) clean

$(pkg)-uninstall:
	$(RM) $(XCLOCK_TARGET_BINARY)

$(PKG_FINISH)
