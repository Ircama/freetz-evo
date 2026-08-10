$(call PKG_INIT_LIB, 0.28.8)
$(PKG)_LIB_VERSION:=0.28.8

# exiv2 0.28.x requires a recent toolchain: older uClibc versions (0.9.x,
# 1.0.14) fail to compile the upstream headers due to -Werror=sign-compare
# warnings. The option is therefore gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58" in Config.in, which disables it on older
# toolchains.

$(PKG)_SOURCE:=v$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=ea51b0609f58a9afa063b60daa1539948b62247721e154f4fff0ad3aec9f9756
$(PKG)_SITE:=https://github.com/Exiv2/exiv2/archive/refs/tags
### WEBSITE:=https://exiv2.org/
### CHANGES:=https://github.com/Exiv2/exiv2/releases
### CVSREPO:=https://github.com/Exiv2/exiv2

$(PKG)_BINARY:=$($(PKG)_DIR)/lib/libexiv2.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libexiv2.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libexiv2.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += expat zlib
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_BUILD_EXIV2_COMMAND=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_BUILD_SAMPLES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_BUILD_UNIT_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_WEBREADY=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_CURL=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_SSH=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_BMFF=ON
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_PNG=ON
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_BROTLI=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_INIH=OFF
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_ENABLE_FILESYSTEM_ACCESS=ON
# Force std::filesystem support: with GCC >= 9, it's built into libstdc++
# and needs no extra link flags. Skip the try_run test which fails in
# cross-compilation.
$(PKG)_CONFIGURE_OPTIONS += -DCXX_FILESYSTEM_NO_LINK_NEEDED=ON
$(PKG)_CONFIGURE_OPTIONS += -DEXIV2_TEAM_WARNINGS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(EXIV2_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(EXIV2_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(EXIV2_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/exiv2 \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libexiv2* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/exiv2.pc

$(pkg)-uninstall:
	$(RM) $(EXIV2_TARGET_DIR)/libexiv2*.so*

$(PKG_FINISH)
