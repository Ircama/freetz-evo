$(call PKG_INIT_LIB, 1.0.11)
$(PKG)_LIB_VERSION:=6.0.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=f3fa3282f5570c3f6bd620244438dbfbdd580fc80f02f549587a0f8ab329bbeb
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
### WEBSITE:=https://www.x.org/

$(PKG)_CATEGORY_LIBS:=X11 graphics
$(PKG)_BINARY:=$($(PKG)_DIR)/.libs/libXau.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXau.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libXau.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += xorgproto
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBXAU_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBXAU_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXau.la

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBXAU_DIR) clean
	$(RM) $(LIBXAU_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXau*

$(pkg)-uninstall:
	$(RM) $(LIBXAU_TARGET_DIR)/libXau*.so*

$(PKG_FINISH)
