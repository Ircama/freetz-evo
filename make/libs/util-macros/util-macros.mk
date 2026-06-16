$(call PKG_INIT_LIB, 1.20.2)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=9ac269eba24f672d7d7b3574e4be5f333d13f04a7712303b1821b2a51ac82e8e
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/util
### WEBSITE:=https://www.x.org/

# Header/macros-only package, no shared library.
# Provides xorg-macros.pc needed by all X.org packages at configure time.
# Install to lib/pkgconfig (not share/pkgconfig) so that the build system's
# default PKG_CONFIG_PATH finds it.
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/xorg-macros.pc

$(PKG)_CONFIGURE_OPTIONS += --with-pkgconfigdir=/usr/lib/pkgconfig

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(UTIL_MACROS_DIR)
	touch $@

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(UTIL_MACROS_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled:

$(pkg)-clean:
	-$(SUBMAKE) -C $(UTIL_MACROS_DIR) clean
	$(RM) $(UTIL_MACROS_DIR)/.configured
	$(RM) $(UTIL_MACROS_DIR)/.compiled
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/xorg-macros.pc
	$(RM) $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/pkgconfig/xorg-macros.pc

$(pkg)-uninstall:

$(PKG_FINISH)
