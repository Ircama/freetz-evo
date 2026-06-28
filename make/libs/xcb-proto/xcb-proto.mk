$(call PKG_INIT_LIB, 1.17.0)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=2c1bacd2110f4799f74de6ebb714b94cf6f80fb112316b1219480fd22562148c
$(PKG)_SITE:=https://xorg.freedesktop.org/archive/individual/proto
### WEBSITE:=https://www.x.org/

# Header-only package, no shared library
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/xcb/xcb.xsd

$(PKG)_DEPENDS_ON += util-macros
$(PKG)_CONFIGURE_OPTIONS += --with-pkgconfigdir=/usr/lib/pkgconfig

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_DIR)/.compiled: $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(XCB_PROTO_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_DIR)/.compiled
	$(SUBMAKE) -C $(XCB_PROTO_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	touch -c $@

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled:

$(pkg)-clean:
	-$(SUBMAKE) -C $(XCB_PROTO_DIR) clean
	$(RM) $(XCB_PROTO_DIR)/.configured
	$(RM) $(XCB_PROTO_DIR)/.compiled

$(pkg)-uninstall:
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/share/xcb

$(PKG_FINISH)
