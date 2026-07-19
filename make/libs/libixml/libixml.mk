$(call PKG_INIT_LIB, 11.1.7)
$(PKG)_LIB_VERSION:=11.1.7
# libixml is part of libupnp, built from the same source
$(PKG)_DEPENDS_ON += libupnp

$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libixml.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libixml.so.$($(PKG)_LIB_VERSION)

# No separate download or unpack - ixml is built and installed by libupnp
# The staging binary is created by libupnp's make install
# Depend on the libupnp target binary to ensure it's installed first
$($(PKG)_STAGING_BINARY): $(TARGET_SPECIFIC_ROOT_DIR)$(FREETZ_LIBRARY_DIR)/libupnp.so.17.2.11
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_TARGET_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libixml.so*

$(PKG_FINISH)
