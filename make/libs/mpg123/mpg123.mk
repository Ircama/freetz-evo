$(call PKG_INIT_LIB, 1.32.10)
# Project version 1.32.10, library SO version 0.48.3
$(PKG)_LIB_VERSION:=0.48.3
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=87b2c17fe0c979d3ef38eeceff6362b35b28ac8589fbf1854b5be75c9ab6557c
$(PKG)_SITE:=https://sourceforge.net/projects/mpg123/files/mpg123/$($(PKG)_VERSION)
### WEBSITE:=https://www.mpg123.de/

$(PKG)_BINARY:=$($(PKG)_DIR)/src/libmpg123/.libs/libmpg123.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmpg123.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libmpg123.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --disable-dependency-tracking
$(PKG)_DEPENDS_ON += alsa-lib

$(PKG)_CONFIGURE_OPTIONS += --with-default-audio=alsa
$(PKG)_CONFIGURE_OPTIONS += --with-optimization=2
$(PKG)_CONFIGURE_OPTIONS += --with-cpu=generic
$(PKG)_CONFIGURE_OPTIONS += --enable-int-quality=no
$(PKG)_CONFIGURE_OPTIONS += --enable-network=no
$(PKG)_CONFIGURE_OPTIONS += --with-audio=alsa
$(PKG)_CONFIGURE_OPTIONS += --with-module=no

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(MPG123_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(MPG123_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(MPG123_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libmpg123.so*

$(PKG_FINISH)
