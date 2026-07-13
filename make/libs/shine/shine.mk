$(call PKG_INIT_LIB, 3.1.1)
# Project version 3.1.1, library SO version 3.0.1
$(PKG)_LIB_VERSION:=3.0.1
$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=565b87867d6f8e6616a236445d194e36f4daa9b4e7af823fcf5010af7610c49e
$(PKG)_SITE:=https://github.com/toots/shine/archive/refs/tags
### WEBSITE:=https://github.com/toots/shine

$(PKG)_BINARY:=$($(PKG)_DIR)/.libs/libshine.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libshine.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libshine.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += autoreconf -fi;

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SHINE_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(SHINE_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(SHINE_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libshine.so*

$(PKG_FINISH)
