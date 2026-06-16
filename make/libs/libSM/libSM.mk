$(call PKG_INIT_LIB, 1.2.4)
$(PKG)_LIB_VERSION:=6.0.1
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=fdcbe51e4d1276b1183da77a8a4e74a137ca203e0bcfb20972dd5f3347e97b84
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
$(PKG)_BINARY:=$($(PKG)_DIR)/.libs/libSM.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libSM.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libSM.so.$($(PKG)_LIB_VERSION)
$(PKG)_DEPENDS_ON += xorgproto libICE
$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --enable-shared --enable-static
$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)
$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBSM_DIR)
$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBSM_DIR) DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libSM.la
$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
$(pkg): $($(PKG)_STAGING_BINARY)
$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)
$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBSM_DIR) clean
	$(RM) $(LIBSM_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libSM*
$(pkg)-uninstall:
	$(RM) $(LIB_SM_TARGET_DIR)/libSM*.so*
$(PKG_FINISH)
