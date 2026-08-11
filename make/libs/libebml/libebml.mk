# libebml 1.4.5 sets CMAKE_CXX_STANDARD 14 (REQUIRED ON) in CMakeLists.txt;
# the old GCC 4.6.4 toolchain does not support C++14 -> cmake configure
# fails ("Target \"ebml\" requires the language dialect \"CXX14\""). The new
# toolchain (GCC 13.4 + uClibc 1.0.58) supports it, hence the
# FREETZ_TARGET_UCLIBC_1_0_58_MIN dependency in Config.in.
$(call PKG_INIT_LIB, 1.4.5)
$(PKG)_LIB_VERSION:=5.0.0
$(PKG)_SOURCE_DOWNLOAD_NAME:=release-$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=86c99573cd0957884f26547d1a8fa0c979e4d6d57484dfd387345846e6720f49
$(PKG)_SITE:=https://github.com/Matroska-Org/libebml/archive/refs/tags
### WEBSITE:=https://github.com/Matroska-Org/libebml
### CHANGES:=https://github.com/Matroska-Org/libebml/releases
### CVSREPO:=https://github.com/Matroska-Org/libebml

$(PKG)_BINARY:=$($(PKG)_DIR)/libebml.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libebml.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libebml.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
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
	$(SUBMAKE) -C $(LIBEBML_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBEBML_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBEBML_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libebml.so*

$(PKG_FINISH)
