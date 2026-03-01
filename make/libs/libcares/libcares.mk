$(call PKG_INIT_LIB, 1.34.6)
$(PKG)_LIB_VERSION:=2
$(PKG)_SOURCE:=c-ares-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=912dd7cc3b3e8a79c52fd7fb9c0f4ecf0aaa73e45efda880266a2d6e26b84ef5
$(PKG)_SITE:=https://github.com/c-ares/c-ares/releases/download/v$($(PKG)_VERSION)
### WEBSITE:=https://c-ares.org/
### MANPAGE:=https://c-ares.org/docs.html
### CHANGES:=https://github.com/c-ares/c-ares/releases
### CVSREPO:=https://github.com/c-ares/c-ares.git
### SUPPORT:=Ircama

$(PKG)_LIBNAMES_SHORT   := libcares
$(PKG)_LIBNAMES_LONG    := $($(PKG)_LIBNAMES_SHORT:%=%.so.$($(PKG)_LIB_VERSION))
$(PKG)_LIBS_BUILD_DIR   := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_DIR)/.libs/%)
$(PKG)_LIBS_STAGING_DIR := $($(PKG)_LIBNAMES_LONG:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%)
$(PKG)_LIBS_TARGET_DIR  := $($(PKG)_LIBNAMES_LONG:%=$($(PKG)_TARGET_DIR)/%)
$(PKG)_LA_STAGING_DIR   := $($(PKG)_LIBNAMES_SHORT:%=$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%.la)

$(PKG)_CONFIGURE_OPTIONS += --enable-shared
$(PKG)_CONFIGURE_OPTIONS += --enable-static
$(PKG)_CONFIGURE_OPTIONS += --prefix=/
$(PKG)_CONFIGURE_OPTIONS += --disable-tests

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_CONFIGURE)

$($(PKG)_LIBS_BUILD_DIR): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(LIBCARES_DIR)

$($(PKG)_LIBS_STAGING_DIR): $($(PKG)_LIBS_BUILD_DIR)
	$(SUBMAKE) -C $(LIBCARES_DIR) \
		DESTDIR="$(TARGET_TOOLCHAIN_STAGING_DIR)" \
		install
	-$(PKG_FIX_LIBTOOL_LA) \
		$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/pkgconfig/libcares.pc

$($(PKG)_LIBS_TARGET_DIR): $($(PKG)_TARGET_DIR)/%: $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/%
	$(INSTALL_LIBRARY_STRIP)

$(pkg): $($(PKG)_LIBS_STAGING_DIR)

$(pkg)-precompiled: $($(PKG)_LIBS_TARGET_DIR)

$(pkg)-clean:
	-[ -f $(LIBCARES_DIR)/Makefile ] && $(MAKE) -C $(LIBCARES_DIR) clean || true

$(pkg)-uninstall:
	$(RM) -r $($(PKG)_TARGET_DIR)

$(PKG_FINISH)
