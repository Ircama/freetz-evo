$(call PKG_INIT_LIB, 2024.1)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=372225fd40815b8423547f5d890c5debc72e88b91088fbfb13158c20495ccb59
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/proto
### WEBSITE:=https://www.x.org/

# Header-only package, no shared library
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/X11/X.h

$(PKG)_DEPENDS_ON += util-macros

$(PKG)_CONFIGURE_OPTIONS += --with-pkgconfigdir=/usr/lib/pkgconfig

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XORGPROTO_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(XORGPROTO_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled:

$(pkg)-clean:
	-$(SUBMAKE) -C $(XORGPROTO_DIR) clean
	$(RM) $(XORGPROTO_DIR)/.configured
	$(RM) $(XORGPROTO_DIR)/.compiled

$(pkg)-uninstall:
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/X11

$(PKG_FINISH)
