$(call PKG_INIT_LIB, 1.3.0)
$(PKG)_LIB_VERSION:=6.0.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=52820b3cdb827d08dc90bdfd1b0022a3ad8919b57a39808b12591973b331bf91
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libXt.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXt.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libXt.so.$($(PKG)_LIB_VERSION)
$(PKG)_DEPENDS_ON += xorgproto libX11 libSM libICE
$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --enable-shared --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-appload --disable-composecache
$(PKG)_CONFIGURE_OPTIONS += --disable-xkb
$(PKG)_CONFIGURE_OPTIONS += --disable-malloc0returnsnull
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBXT_DIR)
$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBXT_DIR) DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXt.la
$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
$(pkg): $($(PKG)_STAGING_BINARY)
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)
$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBXT_DIR) clean
	$(RM) $(LIBXT_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXt*
$(pkg)-uninstall:
	$(RM) $(LIBXT_TARGET_DIR)/libXt*.so*
$(PKG_FINISH)
# DEBUG CHECK
