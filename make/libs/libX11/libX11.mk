$(call PKG_INIT_LIB, 1.8.10)
$(PKG)_LIB_VERSION:=6.4.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=2b3b3dad9347db41dca56beb7db5878f283bde1142f04d9f8e478af435dfdc53
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
### WEBSITE:=https://www.x.org/

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libX11.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libX11.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libX11.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += xorgproto xtrans libxcb
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-xkb
$(PKG)_CONFIGURE_OPTIONS += --disable-xf86bigfont
# malloc(0) does not return NULL on uClibc+NPTL;
# disable to avoid cross-compilation test failure
$(PKG)_CONFIGURE_OPTIONS += --disable-malloc0returnsnull

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBX11_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBX11_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libX11.la

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBX11_DIR) clean
	$(RM) $(LIBX11_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libX11*

$(pkg)-uninstall:
	$(RM) $(LIBX11_TARGET_DIR)/libX11*.so*

$(PKG_FINISH)
