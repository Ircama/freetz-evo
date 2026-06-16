$(call PKG_INIT_LIB, 1.17.0)
$(PKG)_LIB_VERSION:=1.1.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=599ebf9996710fea71622e6e184f3a8ad5b43d0e5fa8c4e407123c88a59a6d55
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
### WEBSITE:=https://www.x.org/

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libxcb.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libxcb.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libxcb.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += xorgproto xcb-proto libXau
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBXCB_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBXCB_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libxcb.la

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBXCB_DIR) clean
	$(RM) $(LIBXCB_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libxcb*

$(pkg)-uninstall:
	$(RM) $(LIBXCB_TARGET_DIR)/libxcb*.so*

$(PKG_FINISH)
