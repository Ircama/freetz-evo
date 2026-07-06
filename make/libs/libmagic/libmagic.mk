$(call PKG_INIT_LIB, 5.47)
$(PKG)_LIB_VERSION:=1.0.0
$(PKG)_SOURCE:=file-$($(PKG)_VERSION).tar.gz
### Use the same source as the file package (file-5.47.tar.gz).
### Build only the shared library component.
$(PKG)_HASH:=45672fec165cb4cc1358a2d76b5d57d22876dcb97ab169427ac385cbe1d5597a
$(PKG)_SITE:=http://ftp.astron.com/pub/file
### WEBSITE:=https://www.darwinsys.com/file/
### CVSREPO:=https://github.com/file/file

$(PKG)_BINARY:=$($(PKG)_DIR)/src/.libs/libmagic.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmagic.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libmagic.so.$($(PKG)_LIB_VERSION)

$(PKG)_DEPENDS_ON += zlib
$(PKG)_DEPENDS_ON += file-host

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-rpath
$(PKG)_CONFIGURE_OPTIONS += --disable-zlib
$(PKG)_CONFIGURE_OPTIONS += --disable-bzlib
$(PKG)_CONFIGURE_OPTIONS += --disable-xzlib
$(PKG)_CONFIGURE_OPTIONS += --disable-zstdlib
$(PKG)_CONFIGURE_OPTIONS += --disable-lzlib
$(PKG)_CONFIGURE_OPTIONS += --disable-libseccomp
$(PKG)_CONFIGURE_OPTIONS += --disable-fsect-man5
$(PKG)_CONFIGURE_OPTIONS += --disable-silent-rules

ifneq ($($(PKG)_SOURCE),$(FILE_HOST_SOURCE))
$(PKG_SOURCE_DOWNLOAD)
endif
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBMAGIC_DIR) \
		FILE_COMPILE="$(abspath $(FILE_HOST_BINARY_TARGET))"

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(LIBMAGIC_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmagic.la

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)

$(pkg)-clean:
	-$(SUBMAKE) -C $(LIBMAGIC_DIR) clean
	$(RM) -r \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/magic.h \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libmagic* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libmagic.pc

$(pkg)-uninstall:
	$(RM) $(LIBMAGIC_TARGET_DIR)/libmagic*.so*

$(PKG_FINISH)
