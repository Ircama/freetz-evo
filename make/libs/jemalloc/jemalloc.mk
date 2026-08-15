$(call PKG_INIT_LIB, 5.3.0)
$(PKG)_LIB_VERSION:=2
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.bz2
$(PKG)_HASH:=2db82d1e7119df3e71b7640219b6dfe84789bc0537983c3b7ac4f7189aecfeaa
$(PKG)_SITE:=https://github.com/jemalloc/jemalloc/releases/download/$($(PKG)_VERSION)
### WEBSITE:=https://jemalloc.net/
### MANPAGE:=https://jemalloc.net/jemalloc.3.html
### CHANGES:=https://github.com/jemalloc/jemalloc/releases
### CVSREPO:=https://github.com/jemalloc/jemalloc

$(PKG)_CATEGORY_LIBS:=Memory allocators
$(PKG)_BINARY:=$($(PKG)_DIR)/lib/libjemalloc.so.$($(PKG)_LIB_VERSION)
$(PKG)_STAGING_BINARY:=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libjemalloc.so.$($(PKG)_LIB_VERSION)
$(PKG)_TARGET_BINARY:=$($(PKG)_TARGET_DIR)/libjemalloc.so.$($(PKG)_LIB_VERSION)

$(PKG)_CONFIGURE_PRE_CMDS += $(call PKG_PREVENT_RPATH_HARDCODING,./configure)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --disable-static
$(PKG)_CONFIGURE_OPTIONS += --disable-debug
$(PKG)_CONFIGURE_OPTIONS += --disable-doc
$(PKG)_CONFIGURE_OPTIONS += --disable-fill
$(PKG)_CONFIGURE_OPTIONS += --disable-prof
$(PKG)_CONFIGURE_OPTIONS += --disable-stats
$(PKG)_CONFIGURE_OPTIONS += --disable-experimental


$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(JEMALLOC_DIR) \
		build_lib_shared

$($(PKG)_STAGING_BINARY): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(JEMALLOC_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install_lib_shared install_include install_bin
	@if [ -f "$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/jemalloc.pc" ]; then \
		$(PKG_FIX_LIBTOOL_LA) \
			$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/jemalloc.pc; \
	fi

$($(PKG)_TARGET_BINARY): $($(PKG)_STAGING_BINARY)
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_STAGING_BINARY)

$(pkg)-precompiled: $($(PKG)_TARGET_BINARY)


$(pkg)-clean:
	-$(SUBMAKE) -C $(JEMALLOC_DIR) clean
	$(RM) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libjemalloc* \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/jemalloc.pc \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/jemalloc-config \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/jemalloc.sh \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/bin/jeprof
	$(RM) -r $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/jemalloc

$(pkg)-uninstall:
	$(RM) $(JEMALLOC_TARGET_DIR)/libjemalloc.so*

$(PKG_FINISH)
