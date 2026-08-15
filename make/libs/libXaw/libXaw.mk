$(call PKG_INIT_LIB, 1.0.16)
$(PKG)_LIB_VERSION:=7.0.0
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=731d572b54c708f81e197a6afa8016918e2e06dfd3025e066ca642a5b8c39c8f
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
### WEBSITE:=https://www.x.org/

$(PKG)_CATEGORY_LIBS:=X11 graphics
$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libXaw7.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw7.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libXaw7.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += xorgproto libX11 libXext libXt libXmu libXpm
$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-xaw6

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBXAW_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBXAW_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw7.la
	ln -sf libXaw7.so $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw.so
	ln -sf libXaw7.so.7 $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw.so.7

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)
	ln -sf libXaw7.so.7 $(dir $@)libXaw.so.7

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBXAW_DIR) clean
	$(RM) $(LIBXAW_DIR)/.configured
	$(RM) $($(PKG)_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw*
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libXaw7*

$(pkg)-uninstall:
	$(RM) $(LIBXAW_TARGET_DIR)/libXaw*.so*

$(PKG_FINISH)
