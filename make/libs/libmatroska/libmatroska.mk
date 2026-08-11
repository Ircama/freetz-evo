# libmatroska 1.7.1 sets CMAKE_CXX_STANDARD 14 (REQUIRED ON) in CMakeLists.txt;
# the old GCC 4.6.4 toolchain does not support C++14. It also selects
# libebml, which has the same requirement, so both are gated on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN in Config.in (no regression for
# uClibc >= 1.0.58 with the new GCC 13.4 toolchain).
$(call PKG_INIT_LIB, 1.7.1)
$(PKG)_LIB_VERSION:=7.0.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=release-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=64763443947833e6c17f1f555f4bb0df6c9f91881810d9d5e0f0bad3622d308b
$(PKG)_SITE:=https://github.com/Matroska-Org/libmatroska/archive/refs/tags
### WEBSITE:=https://github.com/Matroska-Org/libmatroska
### CHANGES:=https://github.com/Matroska-Org/libmatroska/releases
### CVSREPO:=https://github.com/Matroska-Org/libmatroska

$(PKG)_BINARY:=$($(PKG)_DIR)/libmatroska.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmatroska.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libmatroska.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libebml $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_POLICY_VERSION_MINIMUM=3.5

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBMATROSKA_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBMATROSKA_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBMATROSKA_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libmatroska.so*

$(PKG_FINISH)
