$(call PKG_INIT_LIB, 1.3.6)
$(PKG)_LIB_VERSION:=6.4.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=edb59fa23994e405fdc5b400afdf5820ae6160b94f35e3dc3da4457a16e89753
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib

$(PKG)_CATEGORY_LIBS:=X11 graphics
$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libXext.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXext.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libXext.so.$($(PKG)_LIB_VERSION)
$(PKG)_DEPENDS_ON += xorgproto libX11
$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --enable-shared --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-malloc0returnsnull
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBXEXT_DIR)
$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBXEXT_DIR) DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXext.la
$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
$(pkg): $($(PKG)_STAGING_BINARY)
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)
$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBXEXT_DIR) clean
	$(RM) $(LIBXEXT_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXext*
$(pkg)-uninstall:
	$(RM) $(LIBXEXT_TARGET_DIR)/libXext*.so*
$(PKG_FINISH)
