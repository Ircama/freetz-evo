$(call PKG_INIT_LIB, 2.2.3)
$(PKG)_LIB_VERSION:=4.15.1

# libffmpegthumbnailer 2.2.3 requires a recent toolchain: it uses C++11
# std::to_string/std::stoi, which the old uClibc toolchains (0.9.x, 1.0.14)
# do not provide (libstdc++ disables them when _GLIBCXX_USE_C99 is not
# defined for the C library). The option is therefore gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in, which disables it on older
# toolchains.

$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=8c9b9057c6cc8bce9d11701af224c8139c940f734c439a595525e073b09d19b8
$(PKG)_SITE:=https://github.com/dirkvdb/ffmpegthumbnailer/archive/refs/tags
### WEBSITE:=https://github.com/dirkvdb/ffmpegthumbnailer
### CHANGES:=https://github.com/dirkvdb/ffmpegthumbnailer/releases
### CVSREPO:=https://github.com/dirkvdb/ffmpegthumbnailer

$(PKG)_BINARY:=$($(PKG)_DIR)/libffmpegthumbnailer.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libffmpegthumbnailer.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libffmpegthumbnailer.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += ffmpeg
$(PKG)_DEPENDS_ON += $(STDCXXLIB)
$(PKG)_REBUILD_SUBOPTS += FREETZ_STDCXXLIB

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_GIO=OFF
$(PKG)_CONFIGURE_OPTIONS += -DENABLE_THUMBNAILER=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBFFMPEGTHUMBNAILER_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBFFMPEGTHUMBNAILER_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBFFMPEGTHUMBNAILER_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libffmpegthumbnailer.so*

$(PKG_FINISH)
