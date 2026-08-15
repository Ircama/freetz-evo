$(call PKG_INIT_LIB, 3.8.2)
$(PKG)_LIB_VERSION:=13.8.2
$(PKG)_SOURCE:=libarchive-$($(PKG)_VERSION).tar.xz
$(PKG)_HASH:=db0dee91561cbd957689036a3a71281efefd131d35d1d98ebbc32720e4da58e2
$(PKG)_SITE:=https://github.com/libarchive/libarchive/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://www.libarchive.org/
### MANPAGE:=https://github.com/libarchive/libarchive/wiki
### CHANGES:=https://github.com/libarchive/libarchive/releases
### CVSREPO:=https://github.com/libarchive/libarchive

$(PKG)_CATEGORY_LIBS:=Data compression
$(PKG)_BINARY:=$($(PKG)_DIR)/.libs/libarchive.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libarchive.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libarchive.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += zlib bzip2

# Some upstream release archives carry mtimes slightly ahead of the local clock,
# which trips autotools' sanity check during configure.
$(PKG)_CONFIGURE_PRE_CMDS += find . -exec touch -c {} +
$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-bsdtar
$(PKG)_CONFIGURE_OPTIONS += --disable-bsdcat
$(PKG)_CONFIGURE_OPTIONS += --disable-bsdcpio
$(PKG)_CONFIGURE_OPTIONS += --disable-bsdunzip
$(PKG)_CONFIGURE_OPTIONS += --with-zlib
$(PKG)_CONFIGURE_OPTIONS += --with-bz2lib
$(PKG)_CONFIGURE_OPTIONS += --without-libb2
$(PKG)_CONFIGURE_OPTIONS += --without-iconv
$(PKG)_CONFIGURE_OPTIONS += --without-lz4
$(PKG)_CONFIGURE_OPTIONS += --without-zstd
$(PKG)_CONFIGURE_OPTIONS += --without-lzma
$(PKG)_CONFIGURE_OPTIONS += --without-lzo2
$(PKG)_CONFIGURE_OPTIONS += --without-openssl
$(PKG)_CONFIGURE_OPTIONS += --without-nettle
$(PKG)_CONFIGURE_OPTIONS += --without-mbedtls
$(PKG)_CONFIGURE_OPTIONS += --without-xml2
$(PKG)_CONFIGURE_OPTIONS += --without-expat
$(PKG)_CONFIGURE_OPTIONS += --disable-posix-regex-lib
$(PKG)_CONFIGURE_OPTIONS += --disable-acl
$(PKG)_CONFIGURE_OPTIONS += --disable-xattr

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBARCHIVE_DIR)

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBARCHIVE_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libarchive.la \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libarchive.pc

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP_WILDCARD_BEFORE_SO)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBARCHIVE_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libarchive* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libarchive.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/archive.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/archive_entry.h

$(pkg)-uninstall:
	$(RM) $(LIBARCHIVE_TARGET_DIR)/libarchive*.so*

$(PKG_FINISH)