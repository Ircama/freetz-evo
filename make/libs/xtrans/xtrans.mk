$(call PKG_INIT_LIB, 1.5.2)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=5c5cbfe34764a9131d048f03c31c19e57fb4c682d67713eab6a65541b4dff86c
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/lib
### WEBSITE:=https://www.x.org/

# Header-only package, no shared library
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/X11/Xtrans.h

$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --with-pkgconfigdir=/usr/lib/pkgconfig

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XTRANS_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(XTRANS_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled:

$(pkg)-clean:
	-$(SUBMAKE) -C $(XTRANS_DIR) clean
	$(RM) $(XTRANS_DIR)/.configured
	$(RM) $(XTRANS_DIR)/.compiled

$(pkg)-uninstall:

$(PKG_FINISH)
