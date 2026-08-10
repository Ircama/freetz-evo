$(call PKG_INIT_LIB, 12.2.0)
$(PKG)_LIB_VERSION:=12.2.0

# libfmt 12.x requires a recent toolchain: it uses C++ features not
# supported by the old GCC/uClibc toolchains (0.9.x, 1.0.14), which fail to
# compile include/fmt/base.h. The option is therefore gated by "depends on
# FREETZ_TARGET_UCLIBC_1_0_58_MIN" in Config.in, which disables it on older
# toolchains.

$(PKG)_SOURCE_DOWNLOAD_NAME:=$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=8b852bb5aa6e7d8564f9e81394055395dd1d1936d38dfd3a17792a02bebd7af0
$(PKG)_SITE:=https://github.com/fmtlib/fmt/archive/refs/tags
### WEBSITE:=https://fmt.dev/
### CHANGES:=https://github.com/fmtlib/fmt/releases
### CVSREPO:=https://github.com/fmtlib/fmt

$(PKG)_BINARY:=$($(PKG)_DIR)/libfmt.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libfmt.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libfmt.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += cmake-host

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DFMT_TEST=OFF
$(PKG)_CONFIGURE_OPTIONS += -DFMT_DOC=OFF
$(PKG)_CONFIGURE_OPTIONS += -DFMT_INSTALL=ON
$(PKG)_CONFIGURE_OPTIONS += -DFMT_MASTER_PROJECT=ON
$(PKG)_CONFIGURE_OPTIONS += -DBUILD_SHARED_LIBS=ON

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CMAKE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBFMT_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBFMT_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	@touch $@

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBFMT_DIR) clean

$(pkg)-uninstall:
	$(RM) $($(PKG)_TARGET_DIR)/libfmt.so*

$(PKG_FINISH)
