$(call PKG_INIT_LIB, 1.1.1)
$(PKG)_LIB_VERSION:=6.3.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=03e77afaf72942c7ac02ccebb19034e6e20f456dcf8dddadfeb572aa5ad3e451
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib

$(PKG)_CATEGORY_LIBS:=X11 graphics
$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libICE.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libICE.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libICE.so.$($(PKG)_LIB_VERSION)
$(PKG)_DEPENDS_ON += xorgproto
$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --enable-shared --enable-static
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBICE_DIR)
$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBICE_DIR) DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libICE.la
$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
$(pkg): $($(PKG)_STAGING_BINARY)
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)
$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBICE_DIR) clean
	$(RM) $(LIBICE_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libICE*
$(pkg)-uninstall:
	$(RM) $(LIBICE_TARGET_DIR)/libICE*.so*
$(PKG_FINISH)
