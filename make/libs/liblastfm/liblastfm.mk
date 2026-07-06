$(call PKG_INIT_LIB, 1.0.9)
$(PKG)_LIB_VERSION:=1.0.9
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
### HASH placeholder - run: sha256sum dl/liblastfm-1.0.9.tar.gz after download
$(PKG)_HASH:=5276b5fe00932479ce6fe370ba3213f3ab842d70a7d55e4bead6e26738425f7b
$(PKG)_SITE:=https://github.com/lastfm/liblastfm/archive/refs/tags
### WEBSITE:=https://github.com/lastfm/liblastfm
### CHANGES:=https://github.com/lastfm/liblastfm/releases
### CVSREPO:=https://github.com/lastfm/liblastfm

$(PKG)_BINARY:=$($(PKG)_DIR)/src/liblastfm.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/liblastfm.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/liblastfm.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += curl
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

# NOTE: liblastfm requires Qt (QtCore + QtNetwork) which is not available in
# the freetz cross-compilation toolchain. This package is a stub.

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_DEMOS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_TESTS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBLASTFM_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBLASTFM_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBLASTFM_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/liblastfm.so*

$(PKG_FINISH)
