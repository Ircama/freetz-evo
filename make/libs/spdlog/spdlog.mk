$(call PKG_INIT_LIB, 1.17.0)
$(PKG)_LIB_VERSION:=1.17.0

# spdlog requires a recent toolchain (and selects libfmt, which is also
# gated). The option is therefore gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58" in Config.in, which disables it on older
# toolchains.

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=d8862955c6d74e5846b3f580b1605d2428b11d97a410d86e2fb13e857cd3a744
$(PKG)_SITE:=https://github.com/gabime/spdlog/archive/refs/tags
### WEBSITE:=https://github.com/gabime/spdlog
### CHANGES:=https://github.com/gabime/spdlog/releases
### CVSREPO:=https://github.com/gabime/spdlog

$(PKG)_BINARY:=$($(PKG)_DIR)/libspdlog.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libspdlog.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libspdlog.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libfmt

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_BUILD_SHARED=ON
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_BUILD_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_BUILD_EXAMPLE=OFF
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_FMT_EXTERNAL=ON
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_BUILD_PIC=ON
$(PKG)_CONFIGURE_OPTIONS += -DSPDLOG_NO_EXCEPTIONS=OFF

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(SPDLOG_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(SPDLOG_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(SPDLOG_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libspdlog.so*

$(PKG_FINISH)
