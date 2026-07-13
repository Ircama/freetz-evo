$(call PKG_INIT_LIB, 2.4.6)
# Project version 2.4.6, library SO version 3.2.0
$(PKG)_LIB_VERSION:=3.2.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=
$(PKG)_SOURCE:=libshout-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=39cbd4f0efdfddc9755d88217e47f8f2d7108fa767f9d58a2ba26a16d8f7c910
$(PKG)_SITE:=https://downloads.xiph.org/releases/libshout
### WEBSITE:=https://icecast.org/

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libshout.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libshout.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libshout.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += libogg libvorbis libtheora

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBSHOUT_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBSHOUT_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBSHOUT_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libshout.so*

$(PKG_FINISH)
